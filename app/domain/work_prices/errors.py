class DomainError(Exception):
    """Base error for work price domain failures."""


class WorkPriceError(DomainError):
    """Base error for work price-related domain failures."""


class WorkPriceValidationError(WorkPriceError):
    """Raised when work price data violates a domain invariant."""


class WorkPriceNotFoundError(WorkPriceError):
    """Raised when a work price entity cannot be found."""
