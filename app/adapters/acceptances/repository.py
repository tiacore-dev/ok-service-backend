from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
from app.database.managers.materials_manager import AcceptancesManager
from app.domain.acceptances import Acceptance, AcceptanceStatus, AcceptanceStatusHistory
from app.use_cases.acceptances.ports import AcceptanceRepository
from app.use_cases.acceptances.use_cases import AcceptanceHistoryListQuery, AcceptanceListQuery


def _entity(record: dict) -> Acceptance:
    return Acceptance(
        id=UUID(str(record["id"])), date=int(record["date"]),
        project_id=UUID(str(record["project_id"])),
        status=AcceptanceStatus(record["status"]), comment=record.get("comment"),
    )


def _history_entity(record: dict) -> AcceptanceStatusHistory:
    return AcceptanceStatusHistory(
        id=UUID(str(record["id"])),
        acceptance_id=UUID(str(record["acceptance_id"])),
        changed_at=int(record["changed_at"]),
        changed_by=UUID(str(record["changed_by"])),
        from_status=AcceptanceStatus(record["from_status"]),
        to_status=AcceptanceStatus(record["to_status"]),
    )


@dataclass(slots=True)
class SQLAlchemyAcceptanceRepository(AcceptanceRepository):
    manager: AcceptancesManager = field(default_factory=AcceptancesManager)

    def create_acceptance(self, acceptance: Acceptance) -> Acceptance:
        record = normalize_result(self.manager.add(
            id=acceptance.id, date=acceptance.date, project_id=acceptance.project_id,
            status=acceptance.status.value, comment=acceptance.comment,
        ))
        if record is None:
            raise ValueError("Acceptance creation did not return a record")
        return _entity(record)

    def get_acceptance(self, acceptance_id: UUID) -> Acceptance | None:
        record = normalize_result(self.manager.get_by_id(acceptance_id))
        return _entity(record) if record else None

    def update_acceptance(self, acceptance: Acceptance) -> Acceptance | None:
        record = normalize_result(self.manager.update(
            acceptance.id, date=acceptance.date, project_id=acceptance.project_id,
            status=acceptance.status.value, comment=acceptance.comment,
        ))
        return _entity(record) if record else None

    def update_acceptance_with_status_history(
        self, acceptance: Acceptance, history: AcceptanceStatusHistory
    ) -> Acceptance | None:
        record = normalize_result(self.manager.update_with_status_history(
            acceptance.id,
            date=acceptance.date,
            project_id=acceptance.project_id,
            status=acceptance.status.value,
            comment=acceptance.comment,
            history_id=history.id,
            changed_at=history.changed_at,
            changed_by=history.changed_by,
            from_status=history.from_status.value,
            to_status=history.to_status.value,
        ))
        return _entity(record) if record else None

    def delete_acceptance(self, acceptance_id: UUID) -> bool:
        return self.manager.delete(acceptance_id) is not None

    def list_acceptances(self, query: AcceptanceListQuery) -> list[Acceptance]:
        records = self.manager.get_all_filtered(
            offset=query.offset, limit=query.limit, project_id=query.project_id,
            status=query.status.value if query.status else None,
        )
        return [_entity(record) for record in records]

    def list_acceptance_history(
        self, query: AcceptanceHistoryListQuery
    ) -> list[AcceptanceStatusHistory]:
        records = self.manager.get_status_history(
            query.acceptance_id,
            offset=query.offset,
            limit=query.limit if query.limit is not None else 1000,
        )
        return [_history_entity(record) for record in records]
