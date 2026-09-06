"""Custom exception classes for the ELANORA application.

This module contains custom exception classes used throughout the application.

USAGE EXAMPLES:
    # Import the exception
    from app.core.exceptions import RenameConflictError

    # Raise exception with context
    raise RenameConflictError(
        message="File 'example.eaf' already exists",
        conflict_elan_id=123,
        message_key="file_already_exists"
    )

    # Handle exception with context
    try:
        # some operation
        pass
    except RenameConflictError as e:
        logger.error(f"Rename conflict: {e.message_key}", extra={
            "conflict_elan_id": e.conflict_elan_id,
            "project_name": project_name
        })

BEST PRACTICES:
    1. Include relevant context in exception attributes
    2. Use message_key for internationalization support
    3. Document exception behavior in docstrings
    4. Handle exceptions at appropriate levels in the call stack
"""


class RenameConflictError(Exception):
    """Exception raised when a file rename conflicts with an existing file.

    This exception is used when attempting to rename a file to a name that
    already exists in the project, providing context about the conflicting file.

    Attributes:
        conflict_elan_id: The ID of the conflicting ELAN file (optional)
        message_key: A key for internationalization/localization (optional)

    """

    def __init__(
        self,
        message: str,
        conflict_elan_id: int | None = None,
        message_key: str = "rename_conflict",
    ):
        super().__init__(message)
        self.conflict_elan_id = conflict_elan_id
        self.message_key = message_key
