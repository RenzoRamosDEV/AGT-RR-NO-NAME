from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from duelo.application.ingest_commit import ProjectNotFound
from duelo.application.local_projects import HookRemovalFailed, ProjectHasNoFolder
from duelo.application.ports import (
    GithubUnavailable,
    HookInstallError,
    InvalidRepository,
    ProjectAlreadyExists,
    ReviewStartError,
)
from duelo.entrypoints.api.auth import require_ingest_token
from duelo.entrypoints.api.rate_limit import rate_limit
from duelo.entrypoints.api.schemas import (
    AddProjectRequest,
    ErrorResponse,
    ProjectResponse,
    SyncPrsResponse,
)


async def require_local_projects(request: Request) -> None:
    """Con la función apagada, 404 a toda petición (con o sin token): no delata que existe."""
    deps = request.app.state.dependencies
    if not request.app.state.settings.local_projects_enabled or deps.add_local_project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontrado")


# Primero si la función está activa (404), luego el límite y luego el token, como la ingesta.
router = APIRouter(
    tags=["local-projects"],
    dependencies=[
        Depends(require_local_projects),
        Depends(rate_limit("local-projects")),
        Depends(require_ingest_token),
    ],
)

_ERRORS: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
}


@router.post(
    "/projects",
    status_code=status.HTTP_201_CREATED,
    response_model=ProjectResponse,
    responses={**_ERRORS, 409: {"model": ErrorResponse}},
)
async def add_project(body: AddProjectRequest, request: Request) -> ProjectResponse:
    try:
        project = await request.app.state.dependencies.add_local_project(body.path)
    except ProjectAlreadyExists as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese proyecto ya está dado de alta") from exc
    except (InvalidRepository, HookInstallError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return ProjectResponse.from_domain(project)


@router.delete(
    # `path`: los slugs tienen forma `owner/repo` y contienen una barra.
    "/projects/{slug:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**_ERRORS, 409: {"model": ErrorResponse}},
)
async def remove_project(slug: str, request: Request) -> None:
    try:
        await request.app.state.dependencies.remove_project(slug)
    except ProjectNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Proyecto desconocido: {exc.slug}") from exc
    except HookRemovalFailed as exc:
        # El proyecto y su historial se conservan para repetir la baja tras corregir los permisos.
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.post(
    "/projects/{slug:path}/sync-prs",
    response_model=SyncPrsResponse,
    responses={**_ERRORS, 409: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def sync_prs(slug: str, request: Request) -> SyncPrsResponse:
    try:
        result = await request.app.state.dependencies.sync_pull_requests(slug)
    except ProjectNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Proyecto desconocido: {exc.slug}") from exc
    except ProjectHasNoFolder as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except GithubUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except ReviewStartError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "No se pudo arrancar la review, reintenta"
        ) from exc
    return SyncPrsResponse(synced=result.synced, created=result.created)
