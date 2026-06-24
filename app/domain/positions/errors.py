class PositionError(Exception):
    """Base error for position domain failures."""


class PositionValidationError(PositionError):
    """Raised when position data violates a domain invariant."""


class PositionNotFoundError(PositionError):
    """Raised when a position entity cannot be found."""
