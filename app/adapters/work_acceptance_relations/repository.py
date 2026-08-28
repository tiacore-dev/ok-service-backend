from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from app.adapters._typing import normalize_result
from app.database.managers.materials_manager import WorkAcceptanceRelationsManager
from app.domain.work_acceptance_relations import WorkAcceptanceRelation
from app.use_cases.work_acceptance_relations.ports import WorkAcceptanceRelationRepository
from app.use_cases.work_acceptance_relations.use_cases import WorkAcceptanceRelationListQuery


def _entity(record: dict) -> WorkAcceptanceRelation:
    return WorkAcceptanceRelation(
        id=UUID(str(record["id"])), acceptance_id=UUID(str(record["acceptance_id"])),
        work_id=UUID(str(record["work_id"])), quantity=Decimal(str(record["quantity"])),
    )


@dataclass(slots=True)
class SQLAlchemyWorkAcceptanceRelationRepository(WorkAcceptanceRelationRepository):
    manager: WorkAcceptanceRelationsManager = field(default_factory=WorkAcceptanceRelationsManager)

    def create_work_acceptance_relation(self, relation: WorkAcceptanceRelation) -> WorkAcceptanceRelation:
        record = normalize_result(self.manager.add(
            id=relation.id, acceptance_id=relation.acceptance_id,
            work_id=relation.work_id, quantity=relation.quantity,
        ))
        if record is None:
            raise ValueError("Work acceptance relation creation did not return a record")
        return _entity(record)

    def get_work_acceptance_relation(self, relation_id: UUID) -> WorkAcceptanceRelation | None:
        record = normalize_result(self.manager.get_by_id(relation_id))
        return _entity(record) if record else None

    def update_work_acceptance_relation(self, relation: WorkAcceptanceRelation) -> WorkAcceptanceRelation | None:
        record = normalize_result(self.manager.update(
            relation.id, acceptance_id=relation.acceptance_id,
            work_id=relation.work_id, quantity=relation.quantity,
        ))
        return _entity(record) if record else None

    def delete_work_acceptance_relation(self, relation_id: UUID) -> bool:
        return self.manager.delete(relation_id) is not None

    def list_work_acceptance_relations(self, query: WorkAcceptanceRelationListQuery) -> list[WorkAcceptanceRelation]:
        records = self.manager.get_all_filtered(
            offset=query.offset, limit=query.limit,
            acceptance_id=query.acceptance_id, work_id=query.work_id,
        )
        return [_entity(record) for record in records]
