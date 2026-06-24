from __future__ import annotations


class DomainError(Exception):
    """Base error for material domain failures."""


class MaterialError(DomainError):
    """Base error for material-related domain failures."""


class MaterialValidationError(MaterialError):
    """Raised when material data violates a domain invariant."""


class MaterialNotFoundError(MaterialError):
    """Raised when a material entity cannot be found."""
