from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from duelo.config import Settings
from duelo.entrypoints.api.dependencies import ApiDependencies
from duelo.entrypoints.api.routers.health import ready_router
from duelo.entrypoints.api.routers.health import router as health_router
from duelo.entrypoints.api.routers.ingest import router as ingest_router


def create_app(
    settings: Settings | None = None, dependencies: ApiDependencies | None = None
) -> FastAPI:
    """Sin `settings`/`dependencies` solo sirve `/health` (útil para tests y arranque
    mínimo); la composición real la hace `duelo.composition`."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        if dependencies is not None:
            await dependencies.close()

    app = FastAPI(title="Duelo API", lifespan=lifespan)
    app.state.settings = settings
    app.state.dependencies = dependencies
    app.include_router(health_router)
    if settings is not None and dependencies is not None:
        app.include_router(ready_router)
        app.include_router(ingest_router)
    return app
