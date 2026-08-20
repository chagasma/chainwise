import pytest
from chainwise.api.routes import _get_transaction_summary


@pytest.fixture(autouse=True)
def _clear_ttl_caches() -> None:
    """Different tests reuse the same tx_hash with different mocked responses.

    Without this, a `@ttl_cache`d call from one test could leak into the
    next within the cache's TTL window.
    """
    _get_transaction_summary.cache_clear()  # pyright: ignore[reportFunctionMemberAccess]
