from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ShiftReportActor:
    role: str
    user_id: UUID


@dataclass(frozen=True, slots=True)
class CreateShiftReportDetailCommand:
    project_work: UUID | None
    work: UUID
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class CreateShiftReportCommand:
    user: UUID
    date: int
    date_start: int | None = None
    date_end: int | None = None
    project: UUID | None = None
    lng_start: float | None = None
    ltd_start: float | None = None
    lng_end: float | None = None
    ltd_end: float | None = None
    distance_start: float | None = None
    distance_end: float | None = None
    signed: bool = False
    night_shift: bool = False
    extreme_conditions: bool = False
    comment: str | None = None
    details: list[CreateShiftReportDetailCommand] | None = None


@dataclass(frozen=True, slots=True)
class UpdateShiftReportCommand:
    shift_report_id: UUID
    user: UUID | None = None
    date: int | None = None
    date_start: int | None = None
    date_end: int | None = None
    project: UUID | None = None
    lng_start: float | None = None
    ltd_start: float | None = None
    lng_end: float | None = None
    ltd_end: float | None = None
    distance_start: float | None = None
    distance_end: float | None = None
    signed: bool | None = None
    night_shift: bool | None = None
    extreme_conditions: bool | None = None
    deleted: bool | None = None
    comment: str | None = None


@dataclass(frozen=True, slots=True)
class CreateShiftReportDetailPayload:
    shift_report: UUID
    project_work: UUID | None
    work: UUID
    quantity: Decimal
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class UpdateShiftReportDetailCommand:
    shift_report_detail_id: UUID
    shift_report: UUID | None = None
    project_work: UUID | None = None
    work: UUID | None = None
    quantity: Decimal | None = None
