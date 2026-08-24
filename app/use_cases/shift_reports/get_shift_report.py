from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.shift_reports import (
    ShiftReport,
    ShiftReportForbiddenError,
    ShiftReportNotFoundError,
)

from .dto import ShiftReportActor
from .ports import ShiftReportRepository


@dataclass(slots=True)
class GetShiftReportUseCase:
    repository: ShiftReportRepository

    def execute(self, shift_report_id: UUID, actor: ShiftReportActor) -> ShiftReport:
        if actor.role == "user":
            shift_report = self.repository.get_shift_report(shift_report_id)
            if shift_report is None:
                raise ShiftReportNotFoundError("Shift report not found")
            if shift_report.user != actor.user_id:
                raise ShiftReportForbiddenError("Forbidden")
            return shift_report
        shift_report = self.repository.get_shift_report(shift_report_id)
        if shift_report is None:
            raise ShiftReportNotFoundError("Shift report not found")
        return shift_report
