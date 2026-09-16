"""The one place Git operations reach for the same-host recovery copy.

Every Git write that changes a project's files refreshes that copy through
this module, so a test or operator has a single place to intercept it.
"""

from app.utils.project_backup import update_backup

__all__ = ["update_backup"]
