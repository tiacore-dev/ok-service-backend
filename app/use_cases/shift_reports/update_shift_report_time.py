from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.database.time_utils import utc_epoch_milliseconds
from app.domain.shift_reports import (
    ShiftReport,
    ShiftReportConflictError,
    ShiftReportForbiddenError,
    ShiftReportNotFoundError,
)

from .dto import ShiftReportActor, ShiftReportTimeCommand, UpdateShiftReportCommand
from .ports import ShiftReportRepository


@dataclass(slots=True)
class UpdateShiftReportTimeUseCase:
    repository: ShiftReportRepository

    def start(
        self, command: ShiftReportTimeCommand, actor: ShiftReportActor
    ) -> ShiftReport:
        current = self._get_allowed(command.shift_report_id, actor)
        if current.date_start is not None:
            raise ShiftReportConflictError("Shift report has already been started")
        if current.date_end is not None:
            raise ShiftReportConflictError(
                "Shift report has an end time but has not been started"
            )
        return self._update(
            command,
            leave_check_date=current.date,
            date_start=utc_epoch_milliseconds(),
            lng_start=command.lng,
            ltd_start=command.ltd,
        )

    def finish(
        self, command: ShiftReportTimeCommand, actor: ShiftReportActor
    ) -> ShiftReport:
        current = self._get_allowed(command.shift_report_id, actor)
        if current.date_start is None:
            raise ShiftReportConflictError("Shift report has not been started")
        if current.date_end is not None:
            raise ShiftReportConflictError("Shift report has already been finished")
        timestamp = utc_epoch_milliseconds()
        if timestamp < current.date_start:
            raise ShiftReportConflictError("Shift report start time is in the future")
        return self._update(
            command,
            leave_check_date=current.date,
            date_end=timestamp,
            lng_end=command.lng,
            ltd_end=command.ltd,
        )

    def _get_allowed(self, report_id: UUID, actor: ShiftReportActor) -> ShiftReport:
        current = self.repository.get_shift_report(report_id)
        if current is None:
            raise ShiftReportNotFoundError("Shift report not found")
        if current.deleted:
            raise ShiftReportConflictError("Deleted shift report cannot be changed")
        if actor.role == "user" and current.user != actor.user_id:
            raise ShiftReportForbiddenError("User cannot edit not his shift report")
        if actor.role == "user" and current.signed:
            raise ShiftReportForbiddenError("User cannot edit signed shift report")
        return current

    def _update(self, command: ShiftReportTimeCommand, **changes) -> ShiftReport:
        updated = self.repository.update_shift_report(
            UpdateShiftReportCommand(
                shift_report_id=command.shift_report_id,
                updated_by=command.actor_id,
                leave_check_date=changes.pop("leave_check_date", None),
                **changes,
            )
        )
        if updated is None:
            raise ShiftReportNotFoundError("Shift report not found")
        return updated
