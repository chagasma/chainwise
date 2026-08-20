import time

import pytest
from chainwise.cache import ttl_cache


def test_ttl_cache_returns_cached_value_within_ttl() -> None:
    calls = []

    @ttl_cache(seconds=10)
    def fn(x: int) -> int:
        calls.append(x)
        return x * 2

    assert fn(3) == 6
    assert fn(3) == 6
    assert calls == [3]


def test_ttl_cache_refetches_after_expiry() -> None:
    calls = []

    @ttl_cache(seconds=0.01)
    def fn(x: int) -> int:
        calls.append(x)
        return x * 2

    fn(3)
    time.sleep(0.02)
    fn(3)

    assert calls == [3, 3]


def test_ttl_cache_does_not_cache_exceptions() -> None:
    calls = []

    @ttl_cache(seconds=10)
    def fn(x: int) -> int:
        calls.append(x)
        raise ValueError("boom")

    for _ in range(2):
        with pytest.raises(ValueError, match="boom"):
            fn(3)

    assert calls == [3, 3]
