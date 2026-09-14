from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.domain.project_works import ProjectWork, ProjectWorkForbiddenError

from .dto import BulkCreateProjectWorksCommand, CreateProjectWorkCommand, ProjectWorkActor
from .ports import ProjectWorkRepository
from ..time_utils import utc_epoch_milliseconds


def _calculate_summ(price, quantity):
    return price * quantity if price is not None else None


def _owned_project_ids(repository: ProjectWorkRepository, actor: ProjectWorkActor) -> set:
    return set(repository.get_project_ids_by_leader(actor.user_id))


def _ensure_leader_can_use_project(
    repository: ProjectWorkRepository,
    actor: ProjectWorkActor,
    project_id,
    message: str,
) -> None:
    if actor.role != "project-leader":
        return
    owned_project_ids = _owned_project_ids(repository, actor)
    if project_id not in owned_project_ids:
        raise ProjectWorkForbiddenError(message)


@dataclass(slots=True)
class CreateProjectWorkUseCase:
    repository: ProjectWorkRepository

    def execute(
        self, command: CreateProjectWorkCommand, actor: ProjectWorkActor
    ) -> ProjectWork:
        _ensure_leader_can_use_project(
            self.repository, actor, command.project, "You cannot add not your projects"
        )
        project_work = ProjectWork(
            project_work_id=uuid4(),
            project_work_name=command.project_work_name,
            project=command.project,
            work=command.work,
            quantity=command.quantity,
            price=command.price,
            summ=_calculate_summ(command.price, command.quantity),
            created_by=command.created_by or actor.user_id,
            created_at=utc_epoch_milliseconds(),
            signed=False if actor.role == "project-leader" else bool(command.signed),
        )
        return self.repository.create_project_work(project_work)


@dataclass(slots=True)
class BulkCreateProjectWorksUseCase:
    repository: ProjectWorkRepository

    def execute(
        self, command: BulkCreateProjectWorksCommand, actor: ProjectWorkActor
    ) -> list[ProjectWork]:
        if actor.role == "project-leader":
            owned_project_ids = _owned_project_ids(repository=self.repository, actor=actor)
            for item in command.project_works:
                if item.project not in owned_project_ids:
                    raise ProjectWorkForbiddenError(
                        "You cannot add works for projects you do not own"
                    )

        created_project_works = [
            ProjectWork(
                project_work_id=uuid4(),
                project_work_name=item.project_work_name,
                project=item.project,
                work=item.work,
                quantity=item.quantity,
                price=item.price,
                summ=_calculate_summ(item.price, item.quantity),
                created_by=item.created_by or actor.user_id,
                created_at=utc_epoch_milliseconds(),
                signed=False if actor.role == "project-leader" else bool(item.signed),
            )
            for item in command.project_works
        ]
        return self.repository.create_project_works(created_project_works)
