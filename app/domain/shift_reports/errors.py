class DomainError(Exception):
    """Base error for shift report domain failures."""


class ShiftReportError(DomainError):
    """Base error for shift report-related domain failures."""


class ShiftReportValidationError(ShiftReportError):
    """Raised when shift report data violates a domain invariant."""


class ShiftReportConflictError(ShiftReportError):
    """Raised when shift report data conflicts with another business rule."""


class ShiftReportNotFoundError(ShiftReportError):
    """Raised when a shift report entity cannot be found."""


class ShiftReportForbiddenError(ShiftReportError):
    """Raised when actor is not allowed to perform a shift report action."""
