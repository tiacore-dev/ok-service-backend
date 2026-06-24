class ObjectError(Exception):
    """Base error for object domain failures."""


class ObjectValidationError(ObjectError):
    """Raised when object data violates a domain invariant."""


class ObjectNotFoundError(ObjectError):
    """Raised when object cannot be found."""


class ObjectForbiddenError(ObjectError):
    """Raised when actor cannot access the object."""
