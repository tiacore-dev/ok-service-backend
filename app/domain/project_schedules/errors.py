class ProjectScheduleError(Exception):
    """Base error for project schedule domain failures."""


class ProjectScheduleValidationError(ProjectScheduleError):
    """Raised when project schedule data violates a domain invariant."""


class ProjectScheduleNotFoundError(ProjectScheduleError):
    """Raised when project schedule cannot be found."""


class ProjectScheduleForbiddenError(ProjectScheduleError):
    """Raised when actor cannot access the project schedule."""
