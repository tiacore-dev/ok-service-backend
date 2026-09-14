class DomainError(Exception):
    """Base error for acceptance domain failures."""


class AcceptanceValidationError(DomainError):
    """Raised when acceptance data is invalid."""


class AcceptanceNotFoundError(DomainError):
    """Raised when an acceptance cannot be found."""


class AcceptanceForbiddenError(DomainError):
    """Raised when an actor cannot mutate an acceptance."""
