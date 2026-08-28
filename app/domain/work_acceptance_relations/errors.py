class DomainError(Exception):
    """Base error for work acceptance relation domain failures."""


class WorkAcceptanceRelationValidationError(DomainError):
    """Raised when relation data is invalid."""


class WorkAcceptanceRelationNotFoundError(DomainError):
    """Raised when a relation cannot be found."""
