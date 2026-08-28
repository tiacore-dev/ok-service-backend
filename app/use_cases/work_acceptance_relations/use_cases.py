from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.work_acceptance_relations import (
    WorkAcceptanceRelation,
    WorkAcceptanceRelationNotFoundError,
)

from .ports import WorkAcceptanceRelationRepository


@dataclass(frozen=True, slots=True)
class CreateWorkAcceptanceRelationCommand:
    acceptance_id: UUID
    work_id: UUID
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class UpdateWorkAcceptanceRelationCommand:
    id: UUID
    acceptance_id: UUID | None = None
    work_id: UUID | None = None
    quantity: Decimal | None = None


@dataclass(frozen=True, slots=True)
class WorkAcceptanceRelationListQuery:
    offset: int = 0
    limit: int | None = 1000
    acceptance_id: UUID | None = None
    work_id: UUID | None = None


@dataclass(slots=True)
class CreateWorkAcceptanceRelationUseCase:
    repository: WorkAcceptanceRelationRepository

    def execute(self, command: CreateWorkAcceptanceRelationCommand) -> WorkAcceptanceRelation:
        return self.repository.create_work_acceptance_relation(
            WorkAcceptanceRelation(uuid4(), command.acceptance_id, command.work_id, command.quantity)
        )


@dataclass(slots=True)
class GetWorkAcceptanceRelationUseCase:
    repository: WorkAcceptanceRelationRepository

    def execute(self, relation_id: UUID) -> WorkAcceptanceRelation:
        result = self.repository.get_work_acceptance_relation(relation_id)
        if result is None:
            raise WorkAcceptanceRelationNotFoundError("Work acceptance relation not found")
        return result


@dataclass(slots=True)
class ListWorkAcceptanceRelationsUseCase:
    repository: WorkAcceptanceRelationRepository

    def execute(self, query: WorkAcceptanceRelationListQuery) -> list[WorkAcceptanceRelation]:
        return self.repository.list_work_acceptance_relations(query)


@dataclass(slots=True)
class UpdateWorkAcceptanceRelationUseCase:
    repository: WorkAcceptanceRelationRepository

    def execute(self, command: UpdateWorkAcceptanceRelationCommand) -> WorkAcceptanceRelation:
        existing = self.repository.get_work_acceptance_relation(command.id)
        if existing is None:
            raise WorkAcceptanceRelationNotFoundError("Work acceptance relation not found")
        changes = {key: value for key, value in {
            "acceptance_id": command.acceptance_id, "work_id": command.work_id,
            "quantity": command.quantity,
        }.items() if value is not None}
        result = self.repository.update_work_acceptance_relation(existing.with_updates(**changes))
        if result is None:
            raise WorkAcceptanceRelationNotFoundError("Work acceptance relation not found")
        return result


@dataclass(slots=True)
class DeleteWorkAcceptanceRelationUseCase:
    repository: WorkAcceptanceRelationRepository

    def execute(self, relation_id: UUID) -> bool:
        return self.repository.delete_work_acceptance_relation(relation_id)
