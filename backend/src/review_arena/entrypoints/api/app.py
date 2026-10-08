from fastapi import FastAPI

from review_arena.entrypoints.api.routers.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="Review Arena API")
    app.include_router(health_router)
    return app


app = create_app()
