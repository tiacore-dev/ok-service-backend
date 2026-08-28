from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
from app.database.managers.materials_manager import AcceptancesManager
from app.domain.acceptances import Acceptance, AcceptanceStatus
from app.use_cases.acceptances.ports import AcceptanceRepository
from app.use_cases.acceptances.use_cases import AcceptanceListQuery


def _entity(record: dict) -> Acceptance:
    return Acceptance(
        id=UUID(str(record["id"])), date=int(record["date"]),
        project_id=UUID(str(record["project_id"])),
        status=AcceptanceStatus(record["status"]), comment=record.get("comment"),
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

    def delete_acceptance(self, acceptance_id: UUID) -> bool:
        return self.manager.delete(acceptance_id) is not None

    def list_acceptances(self, query: AcceptanceListQuery) -> list[Acceptance]:
        records = self.manager.get_all_filtered(
            offset=query.offset, limit=query.limit, project_id=query.project_id,
            status=query.status.value if query.status else None,
        )
        return [_entity(record) for record in records]
