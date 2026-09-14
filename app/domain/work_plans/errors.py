class WorkPlanError(Exception):
    """Base error for work plan failures."""


class WorkPlanValidationError(WorkPlanError):
    """Raised when a work plan violates a domain invariant."""


class WorkPlanNotFoundError(WorkPlanError):
    """Raised when a work plan cannot be found."""


class WorkPlanForbiddenError(WorkPlanError):
    """Raised when an actor cannot perform a work plan action."""
