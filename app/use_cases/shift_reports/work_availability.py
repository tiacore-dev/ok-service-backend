"""Availability of work types for a shift, based on the performer category.

A work type whose configured price for the performer category is `-1` cannot be
added to the shift or put in place of another work. The rule depends only on
the performer of the shift, not on the user who sends the request. Existing
shift details are never re-checked, so historical records stay readable.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from app.domain.shift_reports import (
    ShiftReportNotFoundError,
    ShiftReportWorkUnavailableError,
)
from app.domain.work_prices import WorkAvailability

from .dto import CreateShiftReportCommand, CreateShiftReportDetailPayload
from .ports import ShiftWorkAvailabilityReader


def ensure_works_available(
    reader: ShiftWorkAvailabilityReader,
    works_by_category: Mapping[int, Iterable[UUID]],
) -> None:
    """Raise once, listing every unavailable work, before anything is written."""
    unavailable: set[UUID] = set()
    for category, work_ids in works_by_category.items():
        ids = set(work_ids)
        if ids:
            unavailable |= reader.get_unavailable_work_ids(ids, category)
    if unavailable:
        raise ShiftReportWorkUnavailableError(unavailable)


def _add(groups: dict[int, set[UUID]], category: int | None, works: Iterable[UUID]):
    # A missing shift or user is reported by the write itself, as before.
    if category is not None:
        groups.setdefault(category, set()).update(works)


def ensure_new_shift_details_available(
    reader: ShiftWorkAvailabilityReader,
    commands: Sequence[CreateShiftReportCommand],
) -> None:
    """Check details sent together with new shifts (single and bulk create)."""
    with_details = [command for command in commands if command.details]
    if not with_details:
        return
    categories = reader.get_user_categories({command.user for command in with_details})
    groups: dict[int, set[UUID]] = {}
    for command in with_details:
        _add(
            groups,
            categories.get(command.user),
            (detail.work for detail in command.details or []),
        )
    ensure_works_available(reader, groups)


def ensure_added_details_available(
    reader: ShiftWorkAvailabilityReader,
    commands: Sequence[CreateShiftReportDetailPayload],
) -> None:
    """Check details added to existing shifts (single and bulk add)."""
    works_by_shift: dict[UUID, set[UUID]] = {}
    for command in commands:
        works_by_shift.setdefault(command.shift_report, set()).add(command.work)
    groups: dict[int, set[UUID]] = {}
    for shift_report_id, works in works_by_shift.items():
        _add(groups, reader.get_shift_report_performer_category(shift_report_id), works)
    ensure_works_available(reader, groups)


@dataclass(slots=True)
class GetShiftWorkAvailabilityUseCase:
    """Availability of works for selection in a shift, for the shift performer."""

    reader: ShiftWorkAvailabilityReader

    def execute(
        self, shift_report_id: UUID, work_ids: Collection[UUID]
    ) -> dict[UUID, WorkAvailability]:
        category = self.reader.get_shift_report_performer_category(shift_report_id)
        if category is None:
            raise ShiftReportNotFoundError("Shift report not found")
        ids = set(work_ids)
        unavailable = (
            self.reader.get_unavailable_work_ids(ids, category) if ids else set()
        )
        return {
            work_id: (
                WorkAvailability.unavailable_for_category()
                if work_id in unavailable
                else WorkAvailability.allowed()
            )
            for work_id in ids
        }
