from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness check: the API process is up. Does not check Postgres or Temporal."""
    return {"status": "ok"}
