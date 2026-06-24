class DomainError(Exception):
    """Base error for work material relation domain failures."""


class WorkMaterialRelationError(DomainError):
    """Base error for work material relation-related domain failures."""


class WorkMaterialRelationValidationError(WorkMaterialRelationError):
    """Raised when work material relation data violates a domain invariant."""


class WorkMaterialRelationNotFoundError(WorkMaterialRelationError):
    """Raised when a work material relation cannot be found."""
