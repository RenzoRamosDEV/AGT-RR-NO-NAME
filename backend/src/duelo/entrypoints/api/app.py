from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from duelo.config import Settings
from duelo.entrypoints.api.dependencies import ApiDependencies
from duelo.entrypoints.api.middleware import REQUEST_ID_HEADER, RequestContextMiddleware
from duelo.entrypoints.api.routers.changes import router as changes_router
from duelo.entrypoints.api.routers.health import ready_router
from duelo.entrypoints.api.routers.health import router as health_router
from duelo.entrypoints.api.routers.ingest import router as ingest_router
from duelo.entrypoints.api.routers.local_projects import router as local_projects_router
from duelo.entrypoints.api.routers.projects import router as projects_router
from duelo.entrypoints.api.routers.reviews import router as reviews_router
from duelo.entrypoints.api.routers.stats import router as stats_router


def create_app(
    settings: Settings | None = None, dependencies: ApiDependencies | None = None
) -> FastAPI:
    """Sin `settings`/`dependencies` solo sirve `/health` (útil para tests y arranque
    mínimo); la composición real la hace `duelo.composition`."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        tasks = (
            [asyncio.create_task(job()) for job in dependencies.background_jobs]
            if dependencies
            else []
        )
        try:
            yield
        finally:
            for task in tasks:
                task.cancel()
            for task in tasks:
                with suppress(asyncio.CancelledError):
                    await task
            if dependencies is not None:
                await dependencies.close()

    app = FastAPI(title="Duelo API", lifespan=lifespan)
    app.state.settings = settings
    app.state.dependencies = dependencies
    if settings is not None and settings.allowed_origins:
        # Orígenes explícitos y sin credenciales: la autenticación va en cabeceras, no en cookies.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Content-Type", "X-Ingest-Token", REQUEST_ID_HEADER],
            expose_headers=[REQUEST_ID_HEADER, "Retry-After"],
            allow_credentials=False,
            max_age=600,
        )
    # El último en añadirse es el más externo: así hasta un preflight lleva `X-Request-ID`.
    app.add_middleware(RequestContextMiddleware)
    app.include_router(health_router)
    if settings is not None and dependencies is not None:
        app.include_router(ready_router)
        app.include_router(ingest_router)
        app.include_router(projects_router)
        app.include_router(local_projects_router)
        app.include_router(changes_router)
        app.include_router(reviews_router)
        app.include_router(stats_router)
    return app
