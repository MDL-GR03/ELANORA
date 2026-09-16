"""What can go wrong when an account's status is changed."""


class AccountNotFoundError(LookupError):
    """The requested account does not exist inside this installation."""


class AccountStatusConflictError(ValueError):
    """The requested account status change is not permitted."""


class SelfAccountStatusError(AccountStatusConflictError):
    """An administrator attempted to change their own account status."""


class LastAdministratorError(AccountStatusConflictError):
    """Suspending the account would leave the institution unadministered."""


class RedundantAccountStatusError(AccountStatusConflictError):
    """The account already has the requested status."""


class AdministratorNoLongerActiveError(PermissionError):
    """The acting administrator was suspended before their request completed."""
