"""Privacy-safe diagnostics for failures crossing process boundaries."""

import re

_SAFE_EXCEPTION_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,79}$")


def safe_exception_type(error: BaseException) -> str:
    """Return a bounded exception class name without exposing its message."""
    name = type(error).__name__
    return name if _SAFE_EXCEPTION_NAME.fullmatch(name) else "Exception"


def safe_failure_summary(error: BaseException, *, operation: str) -> str:
    """Describe a failed operation without copying exception-controlled text."""
    return f"{operation}; error_type={safe_exception_type(error)}"
