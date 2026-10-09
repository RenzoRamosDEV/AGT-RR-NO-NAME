from __future__ import annotations

from types import TracebackType


class FakeSession:
    """Sesión inerte: los repositorios falsos no la usan."""


class FakeSessionFactory:
    """Imita `async_sessionmaker`: se llama y se usa como `async with`."""

    def __call__(self) -> FakeSessionFactory:
        return self

    async def __aenter__(self) -> FakeSession:
        return FakeSession()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        return False
