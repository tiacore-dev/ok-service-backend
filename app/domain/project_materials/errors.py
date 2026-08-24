class DomainError(Exception):
    """Base error for project material domain failures."""


class ProjectMaterialError(DomainError):
    """Base error for project material-related domain failures."""


class ProjectMaterialValidationError(ProjectMaterialError):
    """Raised when project material data violates a domain invariant."""


class ProjectMaterialNotFoundError(ProjectMaterialError):
    """Raised when a project material entity cannot be found."""


class ProjectMaterialForbiddenError(ProjectMaterialError):
    """Raised when an actor cannot add material to a project."""
