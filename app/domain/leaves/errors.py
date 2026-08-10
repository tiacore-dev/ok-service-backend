class DomainError(Exception):
    """Base error for domain-layer failures."""


class LeaveError(DomainError):
    """Base error for leave-related domain failures."""


class LeaveValidationError(LeaveError):
    """Raised when leave data violates a domain invariant."""


class LeaveConflictError(LeaveError):
    """Raised when leave data conflicts with another domain rule."""

    def __init__(
        self, message: str, *, detail: dict[str, object] | None = None
    ) -> None:
        super().__init__(message)
        self.detail = detail


class LeaveNotFoundError(LeaveError):
    """Raised when a leave entity cannot be found."""
