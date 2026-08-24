class PlaceError(Exception):
    """Base error for place domain failures."""


class PlaceValidationError(PlaceError):
    """Raised when place data violates a write invariant."""


class PlaceNotFoundError(PlaceError):
    """Raised when a place cannot be found."""


class PlaceForbiddenError(PlaceError):
    """Raised when an actor cannot change a place."""


class PlaceConflictError(PlaceError):
    """Raised when a place cannot be changed because dependent relations exist."""
