from __future__ import annotations

from dataclasses import dataclass

from app.domain.shift_reports import ShiftReportDetail, ShiftReportNotFoundError

from .dto import UpdateShiftReportDetailCommand
from .ports import ShiftReportRepository
from .work_availability import ensure_works_available


@dataclass(slots=True)
class UpdateShiftReportDetailUseCase:
    repository: ShiftReportRepository

    def execute(self, command: UpdateShiftReportDetailCommand) -> ShiftReportDetail:
        self._ensure_change_allowed(command)
        updated = self.repository.update_shift_report_detail(command)
        if updated is None:
            raise ShiftReportNotFoundError("Shift report detail not found")
        return updated

    def _ensure_change_allowed(self, command: UpdateShiftReportDetailCommand) -> None:
        """Apply the performer-category rule to the resulting detail.

        The rule is checked against the target shift performer and the
        effective work whenever the work, the shift or the quantity changes.
        A quantity change is included because `-1` cannot price the new
        quantity, so the saved accrual would no longer match it. Edits that
        change none of them (e.g. `project_work` only, or resending the same
        values) keep historical details editable.
        """
        if (
            command.work is None
            and command.shift_report is None
            and command.quantity is None
        ):
            return
        current = self.repository.get_shift_report_detail(
            command.shift_report_detail_id
        )
        if current is None:
            raise ShiftReportNotFoundError("Shift report detail not found")

        target_shift = command.shift_report or current.shift_report
        work = command.work or current.work
        shift_changed = target_shift != current.shift_report
        quantity_changed = (
            command.quantity is not None and command.quantity != current.quantity
        )
        if work == current.work and not shift_changed and not quantity_changed:
            return

        category = self.repository.get_shift_report_performer_category(target_shift)
        if category is None:
            if shift_changed:
                raise ShiftReportNotFoundError("Shift report not found")
            return
        ensure_works_available(self.repository, {category: [work]})
