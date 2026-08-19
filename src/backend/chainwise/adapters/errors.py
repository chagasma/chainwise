class AdapterError(Exception):
    """Raised when an external data source can't be reached or misbehaves.

    Base for every adapter's own error (BlockscoutError, future RPCError,
    GitHubError, ...) so routes can catch failures uniformly regardless of
    which adapter raised them.
    """


class AdapterNotFoundError(AdapterError):
    """Raised when the requested resource doesn't exist at the source."""
