from chainwise.agent.checkpointer import _SAFE_SERDE


def test_checkpointer_serde_restricts_to_safe_types() -> None:
    """Regression test for a real bug: setting LANGGRAPH_STRICT_MSGPACK via
    os.environ.setdefault() after importing langgraph.checkpoint.postgres was a
    no-op, because that import reads the env var into a module-level constant
    at import time. Passing allowed_msgpack_modules=None to the serde directly
    sidesteps import ordering entirely — this test locks that behavior in.
    """
    # `True` means "allow anything, warn on unregistered types" (permissive
    # default). `None` means "only SAFE_MSGPACK_TYPES" (the strict mode we want).
    assert _SAFE_SERDE._allowed_msgpack_modules is None
