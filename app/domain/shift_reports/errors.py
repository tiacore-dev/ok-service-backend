from collections.abc import Iterable
from uuid import UUID

from app.domain.work_prices.policies import WORK_UNAVAILABLE_FOR_CATEGORY_MESSAGE


class DomainError(Exception):
    """Base error for shift report domain failures."""


class ShiftReportError(DomainError):
    """Base error for shift report-related domain failures."""


class ShiftReportValidationError(ShiftReportError):
    """Raised when shift report data violates a domain invariant."""


class ShiftReportConflictError(ShiftReportError):
    """Raised when shift report data conflicts with another business rule."""


class ShiftReportNotFoundError(ShiftReportError):
    """Raised when a shift report entity cannot be found."""


class ShiftReportForbiddenError(ShiftReportError):
    """Raised when actor is not allowed to perform a shift report action."""


class ShiftReportWorkUnavailableError(ShiftReportConflictError):
    """Raised when a work type is unavailable for the shift performer category.

    The decision depends on the performer of the shift, never on the actor who
    sends the request.
    """

    code = "WORK_UNAVAILABLE_FOR_PERFORMER_CATEGORY"

    def __init__(self, work_ids: Iterable[UUID]) -> None:
        self.work_ids: tuple[UUID, ...] = tuple(sorted(set(work_ids), key=str))
        super().__init__(WORK_UNAVAILABLE_FOR_CATEGORY_MESSAGE)
