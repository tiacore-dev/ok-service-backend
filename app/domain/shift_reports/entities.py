from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import UUID

from .errors import ShiftReportValidationError


@dataclass(frozen=True, slots=True)
class ShiftReport:
    shift_report_id: UUID
    user: UUID
    date: int
    date_start: int | None
    date_end: int | None
    project: UUID
    lng_start: float | None
    ltd_start: float | None
    lng_end: float | None
    ltd_end: float | None
    distance_start: float | None
    distance_end: float | None
    signed: bool
    deleted: bool
    created_by: UUID
    created_at: int
    night_shift: bool
    extreme_conditions: bool
    number: int
    comment: str | None = None
    signed_at: int | None = None
    signed_by: dict[str, str] | None = None
    updated_at: int | None = None
    updated_by: dict[str, str] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "date", int(self.date))
        object.__setattr__(self, "created_at", int(self.created_at))
        object.__setattr__(self, "signed", bool(self.signed))
        object.__setattr__(self, "deleted", bool(self.deleted))
        object.__setattr__(self, "night_shift", bool(self.night_shift))
        object.__setattr__(self, "extreme_conditions", bool(self.extreme_conditions))
        object.__setattr__(self, "number", int(self.number))
        if self.date < 0:
            raise ShiftReportValidationError(
                "Shift report date must be a positive Unix timestamp."
            )
        if self.date_start is not None and int(self.date_start) < 0:
            raise ShiftReportValidationError(
                "Shift report date_start must be a positive Unix timestamp."
            )
        if self.date_end is not None and int(self.date_end) < 0:
            raise ShiftReportValidationError(
                "Shift report date_end must be a positive Unix timestamp."
            )
    def with_updates(self, **changes) -> "ShiftReport":
        return replace(self, **changes)


@dataclass(frozen=True, slots=True)
class ShiftReportDetail:
    shift_report_detail_id: UUID
    shift_report: UUID
    project_work: UUID | None
    work: UUID
    quantity: Decimal
    summ: Decimal
    created_by: UUID
    created_at: int
    shift_report_user: UUID | None = None
    shift_report_date: int | None = None
    shift_report_project: UUID | None = None
    project_work_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "quantity", Decimal(str(self.quantity)))
        object.__setattr__(self, "summ", Decimal(str(self.summ)))
        object.__setattr__(self, "created_at", int(self.created_at))
        if self.quantity < 0:
            raise ShiftReportValidationError(
                "Shift report detail quantity must be non-negative."
            )

    def with_updates(self, **changes) -> "ShiftReportDetail":
        return replace(self, **changes)
