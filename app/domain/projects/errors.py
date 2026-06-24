class ProjectError(Exception):
    """Base error for project domain failures."""


class ProjectValidationError(ProjectError):
    """Raised when project data violates a domain invariant."""


class ProjectNotFoundError(ProjectError):
    """Raised when project cannot be found."""


class ProjectForbiddenError(ProjectError):
    """Raised when actor cannot access the project."""


class ProjectAlreadyExistsError(ProjectError):
    """Raised when project already exists."""
