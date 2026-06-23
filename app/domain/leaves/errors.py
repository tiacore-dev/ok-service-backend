class DomainError(Exception):
    """Base error for domain-layer failures."""


class LeaveError(DomainError):
    """Base error for leave-related domain failures."""


class LeaveValidationError(LeaveError):
    """Raised when leave data violates a domain invariant."""


class LeaveConflictError(LeaveError):
    """Raised when leave data conflicts with another domain rule."""


class LeaveNotFoundError(LeaveError):
    """Raised when a leave entity cannot be found."""

