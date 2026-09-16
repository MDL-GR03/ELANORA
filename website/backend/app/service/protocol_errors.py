"""What protocol governance refuses, and why."""


class ProtocolConflictError(ValueError):
    """Raised when a requested protocol lifecycle transition is invalid."""


class ProtocolNotFoundError(LookupError):
    """Raised when protocol state is outside the authorized project scope."""
