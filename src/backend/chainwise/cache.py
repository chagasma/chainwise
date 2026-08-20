import time
from collections.abc import Callable
from functools import wraps
from threading import Lock
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def ttl_cache(seconds: float, maxsize: int = 256) -> Callable[[F], F]:
    """Memoizes a function's return value for `seconds`, keyed by its args.
    Unlike `functools.lru_cache`, entries expire — needed for data that's
    usually immutable (a mined tx) but occasionally still "pending". A
    failed call is never cached."""

    def decorator(func: F) -> F:
        store: dict[tuple[Any, ...], tuple[float, Any]] = {}
        lock = Lock()

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = (args, tuple(sorted(kwargs.items())))
            now = time.monotonic()
            with lock:
                cached = store.get(key)
                if cached is not None and cached[0] > now:
                    return cached[1]
            result = func(*args, **kwargs)
            with lock:
                # ponytail: drops an arbitrary (oldest-inserted, not LRU) entry
                # on overflow; fine at this maxsize/TTL, swap for a real LRU
                # structure if eviction quality ever matters.
                if len(store) >= maxsize:
                    store.pop(next(iter(store)))
                store[key] = (now + seconds, result)
            return result

        wrapper.cache_clear = store.clear  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
