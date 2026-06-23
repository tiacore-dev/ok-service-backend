class DomainError(Exception):
    """Base error for project work domain failures."""


class ProjectWorkError(DomainError):
    """Base error for project work-related domain failures."""


class ProjectWorkValidationError(ProjectWorkError):
    """Raised when project work data violates a domain invariant."""


class ProjectWorkNotFoundError(ProjectWorkError):
    """Raised when a project work entity cannot be found."""


class ProjectWorkForbiddenError(ProjectWorkError):
    """Raised when actor is not allowed to perform a project work action."""
