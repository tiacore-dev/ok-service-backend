from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from app.domain.acceptances import (
    Acceptance,
    AcceptanceForbiddenError,
    AcceptanceNotFoundError,
    AcceptanceStatus,
)
from app.use_cases.time_utils import utc_epoch_milliseconds

from .ports import AcceptanceRepository


@dataclass(frozen=True, slots=True)
class AcceptanceActor:
    role: str


@dataclass(frozen=True, slots=True)
class CreateAcceptanceCommand:
    date: int
    project_id: UUID
    status: AcceptanceStatus
    comment: str | None


@dataclass(frozen=True, slots=True)
class UpdateAcceptanceCommand:
    id: UUID
    date: int | None = None
    project_id: UUID | None = None
    status: AcceptanceStatus | None = None
    comment: str | None = None
    comment_provided: bool = False


@dataclass(frozen=True, slots=True)
class AcceptanceListQuery:
    offset: int = 0
    limit: int | None = 1000
    project_id: UUID | None = None
    status: AcceptanceStatus | None = None


def _ensure_mutation(actor: AcceptanceActor) -> None:
    if actor.role not in {"admin", "manager"}:
        raise AcceptanceForbiddenError("Forbidden")


@dataclass(slots=True)
class CreateAcceptanceUseCase:
    repository: AcceptanceRepository

    def execute(self, command: CreateAcceptanceCommand, actor: AcceptanceActor) -> Acceptance:
        _ensure_mutation(actor)
        return self.repository.create_acceptance(
            Acceptance(uuid4(), command.date, command.project_id, command.status, command.comment)
        )


@dataclass(slots=True)
class GetAcceptanceUseCase:
    repository: AcceptanceRepository

    def execute(self, acceptance_id: UUID) -> Acceptance:
        result = self.repository.get_acceptance(acceptance_id)
        if result is None:
            raise AcceptanceNotFoundError("Acceptance not found")
        return result


@dataclass(slots=True)
class ListAcceptancesUseCase:
    repository: AcceptanceRepository

    def execute(self, query: AcceptanceListQuery) -> list[Acceptance]:
        return self.repository.list_acceptances(query)


@dataclass(slots=True)
class UpdateAcceptanceUseCase:
    repository: AcceptanceRepository

    def execute(self, command: UpdateAcceptanceCommand, actor: AcceptanceActor) -> Acceptance:
        _ensure_mutation(actor)
        existing = self.repository.get_acceptance(command.id)
        if existing is None:
            raise AcceptanceNotFoundError("Acceptance not found")
        updated = existing.with_updates(
            **{key: value for key, value in {
                "date": command.date, "project_id": command.project_id,
                "status": command.status,
            }.items() if value is not None}
        )
        if command.comment_provided:
            updated = updated.with_updates(comment=command.comment)
        result = self.repository.update_acceptance(updated)
        if result is None:
            raise AcceptanceNotFoundError("Acceptance not found")
        return result


@dataclass(slots=True)
class DeleteAcceptanceUseCase:
    repository: AcceptanceRepository

    def execute(self, acceptance_id: UUID, actor: AcceptanceActor) -> bool:
        _ensure_mutation(actor)
        return self.repository.delete_acceptance(acceptance_id)
