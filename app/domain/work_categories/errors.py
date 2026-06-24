class DomainError(Exception):
    """Base error for work category domain failures."""


class WorkCategoryError(DomainError):
    """Base error for work category-related domain failures."""


class WorkCategoryValidationError(WorkCategoryError):
    """Raised when work category data violates a domain invariant."""


class WorkCategoryNotFoundError(WorkCategoryError):
    """Raised when a work category entity cannot be found."""
