from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg.rows import DictRow, dict_row

# Restricts checkpoint deserialization to a known-safe allowlist of types, so a
# compromised database can't be used to trigger arbitrary deserialization/code
# execution. Passed explicitly (not via the LANGGRAPH_STRICT_MSGPACK env var):
# that flag is read once at import time by langgraph's msgpack module, so its
# effect depends on import order rather than being guaranteed here.
_SAFE_SERDE = JsonPlusSerializer(allowed_msgpack_modules=None)


@contextmanager
def create_checkpointer(database_url: str) -> Iterator[PostgresSaver]:
    """Opens a Postgres-backed checkpointer for the app's lifetime and runs setup().

    Meant to be entered once in the app's lifespan (not per-request) so the
    connection stays open for as long as the app runs.
    """
    with psycopg.Connection[DictRow].connect(
        database_url, autocommit=True, prepare_threshold=0, row_factory=dict_row
    ) as conn:
        checkpointer = PostgresSaver(conn, serde=_SAFE_SERDE)
        checkpointer.setup()
        yield checkpointer
