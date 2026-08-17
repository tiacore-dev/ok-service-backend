from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.shift_reports import (
    ShiftReport,
    ShiftReportConflictError,
    ShiftReportForbiddenError,
    ShiftReportNotFoundError,
)

from .dto import SHIFT_REPORT_SIGNER_ROLES, ShiftReportActor
from .ports import ShiftReportRepository


@dataclass(slots=True)
class SignShiftReportUseCase:
    repository: ShiftReportRepository

    def execute(self, shift_report_id: UUID, actor: ShiftReportActor) -> ShiftReport:
        if actor.role not in SHIFT_REPORT_SIGNER_ROLES:
            raise ShiftReportForbiddenError("User cannot sign shift report")

        current = self.repository.get_shift_report(shift_report_id)
        if current is None:
            raise ShiftReportNotFoundError("Shift report not found")
        if current.leave_id is not None:
            raise ShiftReportConflictError(
                "Shift report linked to leave cannot be changed"
            )

        signed = self.repository.sign_shift_report(shift_report_id, actor.user_id)
        if signed is None:
            raise ShiftReportNotFoundError("Shift report not found")
        return signed
