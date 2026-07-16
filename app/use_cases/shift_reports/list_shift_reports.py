from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from uuid import UUID

from app.domain.shift_reports import ShiftReport, ShiftReportForbiddenError

from .dto import ShiftReportActor, ShiftReportListQuery
from .ports import ShiftReportRepository


def _owned_project_ids(
    repository: ShiftReportRepository, actor: ShiftReportActor
) -> set[UUID]:
    return {
        UUID(str(project_id))
        for project_id in repository.get_project_ids_by_leader(actor.user_id)
    }


@dataclass(slots=True)
class ListShiftReportsUseCase:
    repository: ShiftReportRepository

    def execute(
        self, query: ShiftReportListQuery, actor: ShiftReportActor
    ) -> tuple[int, list[ShiftReport]]:
        if actor.role == "user":
            query = replace(query, user=[actor.user_id])
        elif actor.role == "project-leader":
            owned_project_ids = _owned_project_ids(self.repository, actor)
            if query.project is None:
                if not owned_project_ids:
                    return 0, []
                query = replace(query, project=list(owned_project_ids))
            elif any(
                project_id not in owned_project_ids for project_id in query.project
            ):
                raise ShiftReportForbiddenError("Forbidden")
        total, reports = self.repository.list_shift_reports(**asdict(query))
        return total, reports
