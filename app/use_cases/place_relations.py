from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid4


class PlaceRelationError(Exception):
    pass


class PlaceRelationNotFoundError(PlaceRelationError):
    pass


class PlaceRelationForbiddenError(PlaceRelationError):
    pass


class PlaceRelationConflictError(PlaceRelationError):
    pass


@dataclass(frozen=True, slots=True)
class RelationActor:
    role: str
    user_id: UUID


@dataclass(frozen=True, slots=True)
class ProjectPlaceRelation:
    project_place_relation_id: UUID
    project_id: UUID
    place_id: UUID


@dataclass(frozen=True, slots=True)
class ShiftPlaceRelation:
    shift_place_relation_id: UUID
    shift_report_id: UUID
    place_id: UUID
    comment: str | None


class PlaceRelationRepository(Protocol):
    def get_project_place_relation(self, relation_id: UUID) -> ProjectPlaceRelation | None: ...
    def create_project_place_relation(self, relation: ProjectPlaceRelation) -> ProjectPlaceRelation: ...
    def update_project_place_relation(self, relation: ProjectPlaceRelation) -> ProjectPlaceRelation | None: ...
    def delete_project_place_relation(self, relation_id: UUID) -> bool: ...
    def list_project_place_relations(self) -> list[ProjectPlaceRelation]: ...
    def get_shift_place_relation(self, relation_id: UUID) -> ShiftPlaceRelation | None: ...
    def create_shift_place_relation(self, relation: ShiftPlaceRelation) -> ShiftPlaceRelation: ...
    def update_shift_place_relation(self, relation: ShiftPlaceRelation) -> ShiftPlaceRelation | None: ...
    def delete_shift_place_relation(self, relation_id: UUID) -> bool: ...
    def list_shift_place_relations(self) -> list[ShiftPlaceRelation]: ...
    def project_object_id(self, project_id: UUID) -> UUID | None: ...
    def place_object_id(self, place_id: UUID) -> UUID | None: ...
    def project_leader_id(self, project_id: UUID) -> UUID | None: ...
    def shift_context(self, shift_report_id: UUID) -> tuple[UUID, UUID] | None: ...
    def has_project_place(self, project_id: UUID, place_id: UUID) -> bool: ...
    def has_shift_place(self, shift_report_id: UUID, place_id: UUID) -> bool: ...
    def is_place_used_by_shift(self, project_id: UUID, place_id: UUID) -> bool: ...


def _privileged(actor: RelationActor) -> bool:
    return actor.role in {"admin", "manager"}


def _project_allowed(repository: PlaceRelationRepository, project_id: UUID, actor: RelationActor) -> bool:
    return _privileged(actor) or (
        actor.role == "project-leader"
        and repository.project_leader_id(project_id) == actor.user_id
    )


def _shift_allowed(repository: PlaceRelationRepository, shift_report_id: UUID, actor: RelationActor) -> bool:
    context = repository.shift_context(shift_report_id)
    if context is None:
        return False
    project_id, user_id = context
    return _privileged(actor) or (
        actor.role == "user" and user_id == actor.user_id
    ) or (
        actor.role == "project-leader"
        and repository.project_leader_id(project_id) == actor.user_id
    )


def _check_project_place(repository, project_id, place_id):
    project_object = repository.project_object_id(project_id)
    place_object = repository.place_object_id(place_id)
    if project_object is None or place_object is None:
        raise PlaceRelationNotFoundError("Project or place not found")
    if project_object != place_object:
        raise PlaceRelationConflictError("Project and place objects must match")


@dataclass(slots=True)
class PlaceRelationService:
    repository: PlaceRelationRepository

    def create_project_place(self, project_id, place_id, actor):
        if not _project_allowed(self.repository, project_id, actor):
            raise PlaceRelationForbiddenError("Forbidden")
        _check_project_place(self.repository, project_id, place_id)
        if self.repository.has_project_place(project_id, place_id):
            raise PlaceRelationConflictError("Place is already linked to project")
        return self.repository.create_project_place_relation(
            ProjectPlaceRelation(uuid4(), project_id, place_id)
        )

    def update_project_place(self, relation_id, project_id, place_id, actor):
        current = self.repository.get_project_place_relation(relation_id)
        if current is None:
            raise PlaceRelationNotFoundError("Project place relation not found")
        if not _project_allowed(self.repository, current.project_id, actor):
            raise PlaceRelationForbiddenError("Forbidden")
        _check_project_place(self.repository, project_id, place_id)
        if (project_id, place_id) != (current.project_id, current.place_id) and self.repository.has_project_place(project_id, place_id):
            raise PlaceRelationConflictError("Place is already linked to project")
        if self.repository.is_place_used_by_shift(current.project_id, current.place_id):
            raise PlaceRelationConflictError("Project place is used by a shift")
        result = self.repository.update_project_place_relation(
            ProjectPlaceRelation(relation_id, project_id, place_id)
        )
        if result is None:
            raise PlaceRelationNotFoundError("Project place relation not found")
        return result

    def delete_project_place(self, relation_id, actor):
        current = self.repository.get_project_place_relation(relation_id)
        if current is None:
            raise PlaceRelationNotFoundError("Project place relation not found")
        if not _project_allowed(self.repository, current.project_id, actor):
            raise PlaceRelationForbiddenError("Forbidden")
        if self.repository.is_place_used_by_shift(current.project_id, current.place_id):
            raise PlaceRelationConflictError("Project place is used by a shift")
        if not self.repository.delete_project_place_relation(relation_id):
            raise PlaceRelationNotFoundError("Project place relation not found")

    def create_shift_place(self, shift_report_id, place_id, comment, actor):
        if not _shift_allowed(self.repository, shift_report_id, actor):
            raise PlaceRelationForbiddenError("Forbidden")
        context = self.repository.shift_context(shift_report_id)
        if context is None:
            raise PlaceRelationNotFoundError("Shift report not found")
        if not self.repository.has_project_place(context[0], place_id):
            raise PlaceRelationConflictError("Place is not linked to shift project")
        if self.repository.has_shift_place(shift_report_id, place_id):
            raise PlaceRelationConflictError("Place is already linked to shift")
        return self.repository.create_shift_place_relation(
            ShiftPlaceRelation(uuid4(), shift_report_id, place_id, comment)
        )

    def update_shift_place(self, relation_id, place_id, comment, actor):
        current = self.repository.get_shift_place_relation(relation_id)
        if current is None:
            raise PlaceRelationNotFoundError("Shift place relation not found")
        if not _shift_allowed(self.repository, current.shift_report_id, actor):
            raise PlaceRelationForbiddenError("Forbidden")
        context = self.repository.shift_context(current.shift_report_id)
        if context is None or not self.repository.has_project_place(context[0], place_id):
            raise PlaceRelationConflictError("Place is not linked to shift project")
        if place_id != current.place_id and self.repository.has_shift_place(current.shift_report_id, place_id):
            raise PlaceRelationConflictError("Place is already linked to shift")
        result = self.repository.update_shift_place_relation(
            ShiftPlaceRelation(relation_id, current.shift_report_id, place_id, comment)
        )
        if result is None:
            raise PlaceRelationNotFoundError("Shift place relation not found")
        return result

    def delete_shift_place(self, relation_id, actor):
        current = self.repository.get_shift_place_relation(relation_id)
        if current is None:
            raise PlaceRelationNotFoundError("Shift place relation not found")
        if not _shift_allowed(self.repository, current.shift_report_id, actor):
            raise PlaceRelationForbiddenError("Forbidden")
        if not self.repository.delete_shift_place_relation(relation_id):
            raise PlaceRelationNotFoundError("Shift place relation not found")
