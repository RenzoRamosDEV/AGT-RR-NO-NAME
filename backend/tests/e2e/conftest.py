"""El E2E reutiliza la infraestructura de los tests de integración (Postgres con
testcontainers y servidor de test de Temporal)."""

from tests.integration.conftest import (  # noqa: F401
    database_url,
    engine,
    session_factory,
    temporal_env,
)
