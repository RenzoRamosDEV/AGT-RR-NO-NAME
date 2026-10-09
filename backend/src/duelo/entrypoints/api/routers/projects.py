from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError

from duelo.application.ingest_commit import ProjectNotFound
from duelo.domain.change import ChangeKind
from duelo.entrypoints.api.cursor import InvalidCursor, decode_cursor, encode_cursor
from duelo.entrypoints.api.schemas import ChangePageResponse, ErrorResponse, ProjectResponse

router = APIRouter(tags=["projects"])

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(request: Request) -> list[ProjectResponse]:
    projects = await request.app.state.dependencies.list_projects()
    return [ProjectResponse.from_domain(p) for p in projects]


@router.get(
    # `path`: los slugs tienen forma `owner/repo` y contienen una barra.
    "/projects/{slug:path}/changes",
    response_model=ChangePageResponse,
    responses={404: {"model": ErrorResponse}},
)
async def list_changes(
    slug: str,
    request: Request,
    kind: ChangeKind | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
) -> ChangePageResponse:
    try:
        after = decode_cursor(cursor) if cursor is not None else None
    except InvalidCursor as exc:
        # Mismo formato que cualquier otro 422 de validación de parámetros.
        error = {
            "type": "value_error",
            "loc": ("query", "cursor"),
            "msg": str(exc),
            "input": cursor,
        }
        raise RequestValidationError([error]) from exc
    try:
        page = await request.app.state.dependencies.list_changes(slug, kind, limit, after)
    except ProjectNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Proyecto desconocido: {exc.slug}") from exc
    next_cursor = encode_cursor(page.next_cursor) if page.next_cursor is not None else None
    return ChangePageResponse.from_page(page, next_cursor)
