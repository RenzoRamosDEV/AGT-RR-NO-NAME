import pytest

from duelo.adapters.ratelimit.in_memory import InMemoryRateLimiter


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _limiter(clock: Clock, *, limit: int = 3, window: float = 60, max_keys: int = 10_000):
    return InMemoryRateLimiter(limit=limit, window_seconds=window, clock=clock, max_keys=max_keys)


async def test_requests_up_to_the_limit_are_allowed_and_the_next_is_rejected() -> None:
    clock = Clock()
    limiter = _limiter(clock)

    allowed = [(await limiter.hit("ip")).allowed for _ in range(4)]

    assert allowed == [True, True, True, False]


async def test_retry_after_is_the_time_until_the_oldest_hit_leaves_the_window() -> None:
    clock = Clock()
    limiter = _limiter(clock, limit=2, window=60)
    await limiter.hit("ip")  # t=1000
    clock.now += 10.5
    await limiter.hit("ip")  # t=1010.5

    clock.now += 4.2  # t=1014.7: la primera sale en t=1060 -> 45.3 s -> se redondea hacia arriba
    decision = await limiter.hit("ip")

    assert not decision.allowed
    assert decision.retry_after_seconds == 46


async def test_retry_after_is_at_least_one_second() -> None:
    clock = Clock()
    limiter = _limiter(clock, limit=1, window=60)
    await limiter.hit("ip")
    clock.now += 59.9999

    assert (await limiter.hit("ip")).retry_after_seconds == 1


async def test_the_window_slides_instead_of_resetting_all_at_once() -> None:
    clock = Clock()
    limiter = _limiter(clock, limit=2, window=60)
    await limiter.hit("ip")  # t=1000
    clock.now += 30
    await limiter.hit("ip")  # t=1030
    assert not (await limiter.hit("ip")).allowed

    clock.now = 1060  # la de t=1000 ya salió (<= cutoff), la de t=1030 sigue dentro
    assert (await limiter.hit("ip")).allowed
    assert not (await limiter.hit("ip")).allowed


async def test_rejected_requests_do_not_extend_the_block() -> None:
    clock = Clock()
    limiter = _limiter(clock, limit=1, window=10)
    await limiter.hit("ip")  # t=1000
    for _ in range(5):
        clock.now += 1
        assert not (await limiter.hit("ip")).allowed

    clock.now = 1010  # 10 s tras la única petición aceptada
    assert (await limiter.hit("ip")).allowed


async def test_keys_are_independent() -> None:
    limiter = _limiter(Clock(), limit=1)

    assert (await limiter.hit("a")).allowed
    assert not (await limiter.hit("a")).allowed
    assert (await limiter.hit("b")).allowed


async def test_memory_is_bounded_by_dropping_idle_keys_first() -> None:
    clock = Clock()
    limiter = _limiter(clock, limit=5, window=60, max_keys=3)
    for key in ("a", "b", "c"):
        await limiter.hit(key)
    clock.now += 61  # a, b y c quedan inactivas

    await limiter.hit("d")

    assert set(limiter._hits) == {"d"}  # noqa: SLF001 - se comprueba la cota de memoria


async def test_memory_is_bounded_even_if_every_key_is_active() -> None:
    limiter = _limiter(Clock(), limit=5, window=60, max_keys=3)

    for key in ("a", "b", "c", "d", "e"):
        await limiter.hit(key)

    assert list(limiter._hits) == ["c", "d", "e"]  # noqa: SLF001 - salen las más antiguas


@pytest.mark.parametrize(
    "kwargs", [{"limit": 0}, {"window_seconds": 0}, {"window_seconds": -1}, {"max_keys": 0}]
)
def test_invalid_parameters_are_rejected(kwargs: dict[str, float]) -> None:
    params = {"limit": 1, "window_seconds": 1, "max_keys": 1} | kwargs

    with pytest.raises(ValueError, match="positivos"):
        InMemoryRateLimiter(**params)  # type: ignore[arg-type]
