from __future__ import annotations

from dataclasses import dataclass, replace

from app.domain.projects import ProjectStatus
from app.domain.shift_reports import (
    ShiftReport,
    ShiftReportForbiddenError,
    ShiftReportValidationError,
)

from .dto import CreateShiftReportCommand, ShiftReportActor
from .ports import ShiftReportRepository


@dataclass(slots=True)
class CreateShiftReportUseCase:
    repository: ShiftReportRepository

    def execute(
        self, command: CreateShiftReportCommand, actor: ShiftReportActor
    ) -> ShiftReport:
        if actor.role == "user":
            raise ShiftReportForbiddenError("User cannot create shift report")
        if command.project is not None:
            project_status = self.repository.get_project_status(command.project)
            if project_status is None:
                raise ShiftReportValidationError("Project not found")
            if project_status is not ProjectStatus.IN_PROGRESS:
                raise ShiftReportValidationError(
                    "Shift report can be created only for a project in progress"
                )
        if (
            command.date_start is not None
            and command.date_end is not None
            and command.date_end < command.date_start
        ):
            raise ShiftReportValidationError(
                "Shift report date_end must be greater than or equal to date_start."
            )
        command = replace(command, created_by=actor.user_id)
        return self.repository.create_shift_report(command)
