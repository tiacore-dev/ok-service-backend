from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from app.domain.acceptances import (
    Acceptance,
    AcceptanceForbiddenError,
    AcceptanceNotFoundError,
    AcceptanceStatus,
    AcceptanceStatusHistory,
)
from app.use_cases.time_utils import utc_epoch_milliseconds

from .ports import AcceptanceRepository


@dataclass(frozen=True, slots=True)
class AcceptanceActor:
    role: str
    user_id: UUID


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
    project_leader_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class AcceptanceHistoryListQuery:
    acceptance_id: UUID
    offset: int = 0
    limit: int | None = 1000


def _ensure_mutation(actor: AcceptanceActor) -> None:
    if actor.role not in {"admin", "manager"}:
        raise AcceptanceForbiddenError("Forbidden")


def _ensure_object_not_waiting(repository: AcceptanceRepository, project_id: UUID) -> None:
    get_status = getattr(repository, "get_project_object_status", None)
    if get_status is not None and get_status(project_id) == "waiting":
        raise ValueError(
            "Acceptances cannot be created or edited while the object is waiting"
        )


def _ensure_leader_access(repository: AcceptanceRepository, project_id: UUID, actor: AcceptanceActor) -> None:
    if actor.role != "project-leader":
        if actor.role in {"admin", "manager"}:
            return
        raise AcceptanceForbiddenError("Forbidden")
    get_leader_id = getattr(repository, "get_project_leader_id", None)
    if get_leader_id is None or get_leader_id(project_id) != actor.user_id:
        raise AcceptanceForbiddenError("Forbidden")


@dataclass(slots=True)
class CreateAcceptanceUseCase:
    repository: AcceptanceRepository

    def execute(self, command: CreateAcceptanceCommand, actor: AcceptanceActor) -> Acceptance:
        _ensure_mutation(actor)
        _ensure_object_not_waiting(self.repository, command.project_id)
        return self.repository.create_acceptance(
            Acceptance(uuid4(), command.date, command.project_id, command.status, command.comment)
        )


@dataclass(slots=True)
class GetAcceptanceUseCase:
    repository: AcceptanceRepository

    def execute(self, acceptance_id: UUID, actor: AcceptanceActor | None = None) -> Acceptance:
        result = self.repository.get_acceptance(acceptance_id)
        if result is None:
            raise AcceptanceNotFoundError("Acceptance not found")
        if actor is not None:
            _ensure_leader_access(self.repository, result.project_id, actor)
        return result


@dataclass(slots=True)
class ListAcceptancesUseCase:
    repository: AcceptanceRepository

    def execute(self, query: AcceptanceListQuery, actor: AcceptanceActor | None = None) -> list[Acceptance]:
        if actor is not None and actor.role not in {"admin", "manager", "project-leader"}:
            raise AcceptanceForbiddenError("Forbidden")
        if actor is not None and actor.role == "project-leader":
            query = replace(query, project_leader_id=actor.user_id)
        return self.repository.list_acceptances(query)


@dataclass(slots=True)
class UpdateAcceptanceUseCase:
    repository: AcceptanceRepository

    def execute(self, command: UpdateAcceptanceCommand, actor: AcceptanceActor) -> Acceptance:
        _ensure_mutation(actor)
        existing = self.repository.get_acceptance(command.id)
        if existing is None:
            raise AcceptanceNotFoundError("Acceptance not found")
        if existing.status is AcceptanceStatus.DOCUMENTS_SIGNED and actor.role != "admin":
            raise AcceptanceForbiddenError(
                "Only admin can edit an acceptance with signed documents"
            )
        _ensure_object_not_waiting(
            self.repository, command.project_id or existing.project_id
        )
        updated = existing.with_updates(
            **{key: value for key, value in {
                "date": command.date, "project_id": command.project_id,
                "status": command.status,
            }.items() if value is not None}
        )
        if command.comment_provided:
            updated = updated.with_updates(comment=command.comment)
        if updated.status != existing.status:
            history = AcceptanceStatusHistory(
                id=uuid4(),
                acceptance_id=existing.id,
                changed_at=utc_epoch_milliseconds(),
                changed_by=actor.user_id,
                from_status=existing.status,
                to_status=updated.status,
            )
            result = self.repository.update_acceptance_with_status_history(
                updated, history
            )
        else:
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


@dataclass(slots=True)
class ListAcceptanceHistoryUseCase:
    repository: AcceptanceRepository

    def execute(self, query: AcceptanceHistoryListQuery) -> list[AcceptanceStatusHistory]:
        return self.repository.list_acceptance_history(query)
