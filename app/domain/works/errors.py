class WorkError(Exception):
    """Base error for work domain failures."""


class WorkValidationError(WorkError):
    """Raised when work data violates a domain invariant."""


class WorkNotFoundError(WorkError):
    """Raised when work cannot be found."""
