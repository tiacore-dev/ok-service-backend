from __future__ import annotations


class DomainError(Exception):
    """Base error for shift report material domain failures."""


class ShiftReportMaterialError(DomainError):
    """Base error for shift report material-related domain failures."""


class ShiftReportMaterialValidationError(ShiftReportMaterialError):
    """Raised when shift report material data violates a domain invariant."""


class ShiftReportMaterialNotFoundError(ShiftReportMaterialError):
    """Raised when a shift report material entity cannot be found."""
