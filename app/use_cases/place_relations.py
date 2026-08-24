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
class ShiftContext:
    project_id: UUID
    user_id: UUID
    signed: bool


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
    def shift_context(self, shift_report_id: UUID) -> ShiftContext | None: ...
    def has_project_place(self, project_id: UUID, place_id: UUID) -> bool: ...
    def has_shift_place(self, shift_report_id: UUID, place_id: UUID) -> bool: ...
    def is_place_used_by_shift(self, project_id: UUID, place_id: UUID) -> bool: ...
    def bulk_create_project_place_relations(self, relations: list[ProjectPlaceRelation]) -> list[ProjectPlaceRelation]: ...
    def bulk_delete_project_place_relations(self, relation_ids: list[UUID]) -> int: ...
    def bulk_create_shift_place_relations(self, relations: list[ShiftPlaceRelation]) -> list[ShiftPlaceRelation]: ...
    def bulk_delete_shift_place_relations(self, relation_ids: list[UUID]) -> int: ...


def _privileged(actor: RelationActor) -> bool:
    return actor.role in {"admin", "manager"}


def _project_allowed(repository: PlaceRelationRepository, project_id: UUID, actor: RelationActor) -> bool:
    return _privileged(actor) or (
        actor.role == "project-leader"
        and repository.project_leader_id(project_id) == actor.user_id
    )


def _project_view_allowed(actor: RelationActor) -> bool:
    return actor.role in {"admin", "manager", "project-leader"}


def _shift_view_allowed(repository: PlaceRelationRepository, shift_report_id: UUID, actor: RelationActor) -> bool:
    context = repository.shift_context(shift_report_id)
    if context is None:
        return False
    return actor.role in {"admin", "manager", "project-leader"} or (
        actor.role == "user" and context.user_id == actor.user_id
    )


def _shift_mutation_allowed(repository: PlaceRelationRepository, shift_report_id: UUID, actor: RelationActor) -> bool:
    context = repository.shift_context(shift_report_id)
    if context is None:
        return False
    if actor.role == "admin":
        return True
    if actor.role == "project-leader":
        return repository.project_leader_id(context.project_id) == actor.user_id
    return actor.role == "user" and not context.signed and context.user_id == actor.user_id


def _require_project_view(actor: RelationActor) -> None:
    if not _project_view_allowed(actor):
        raise PlaceRelationForbiddenError("Forbidden")


def _require_shift_view(repository: PlaceRelationRepository, shift_report_id: UUID, actor: RelationActor) -> None:
    if not _shift_view_allowed(repository, shift_report_id, actor):
        raise PlaceRelationForbiddenError("Forbidden")


def _require_shift_mutation(repository: PlaceRelationRepository, shift_report_id: UUID, actor: RelationActor) -> None:
    if not _shift_mutation_allowed(repository, shift_report_id, actor):
        raise PlaceRelationForbiddenError("Forbidden")


def _shift_allowed(repository: PlaceRelationRepository, shift_report_id: UUID, actor: RelationActor) -> bool:
    return _shift_mutation_allowed(repository, shift_report_id, actor)


def _check_project_place(repository, project_id, place_id):
    project_object = repository.project_object_id(project_id)
    place_object = repository.place_object_id(place_id)
    if project_object is None or place_object is None:
        raise PlaceRelationNotFoundError("Project or place not found")
    if project_object != place_object:
        raise PlaceRelationConflictError("Project and place objects must match")


def _unique_place_ids(place_ids: list[UUID]) -> list[UUID]:
    return list(dict.fromkeys(place_ids))


@dataclass(slots=True)
class PlaceRelationService:
    repository: PlaceRelationRepository

    def get_project_place(self, relation_id, actor):
        _require_project_view(actor)
        current = self.repository.get_project_place_relation(relation_id)
        if current is None:
            raise PlaceRelationNotFoundError("Project place relation not found")
        return current

    def list_project_places(self, actor):
        _require_project_view(actor)
        return self.repository.list_project_place_relations()

    def get_shift_place(self, relation_id, actor):
        current = self.repository.get_shift_place_relation(relation_id)
        if current is None:
            raise PlaceRelationNotFoundError("Shift place relation not found")
        _require_shift_view(self.repository, current.shift_report_id, actor)
        return current

    def list_shift_places(self, actor):
        relations = self.repository.list_shift_place_relations()
        return [
            relation
            for relation in relations
            if _shift_view_allowed(self.repository, relation.shift_report_id, actor)
        ]

    def create_project_place(self, project_id, place_id, actor):
        if not _project_allowed(self.repository, project_id, actor):
            raise PlaceRelationForbiddenError("Forbidden")
        _check_project_place(self.repository, project_id, place_id)
        if self.repository.has_project_place(project_id, place_id):
            raise PlaceRelationConflictError("Place is already linked to project")
        return self.repository.create_project_place_relation(
            ProjectPlaceRelation(uuid4(), project_id, place_id)
        )

    def bulk_create_project_places(self, project_id, place_ids, actor):
        if not _project_allowed(self.repository, project_id, actor):
            raise PlaceRelationForbiddenError("Forbidden")
        relations = []
        for place_id in _unique_place_ids(place_ids):
            _check_project_place(self.repository, project_id, place_id)
            if not self.repository.has_project_place(project_id, place_id):
                relations.append(ProjectPlaceRelation(uuid4(), project_id, place_id))
        return self.repository.bulk_create_project_place_relations(relations) if relations else []

    def update_project_place(self, relation_id, project_id, place_id, actor):
        raise PlaceRelationForbiddenError("Project place relations cannot be edited")

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

    def bulk_delete_project_places(self, project_id, place_ids, actor):
        if not _project_allowed(self.repository, project_id, actor):
            raise PlaceRelationForbiddenError("Forbidden")
        requested = set(_unique_place_ids(place_ids))
        relation_ids = []
        for relation in self.repository.list_project_place_relations():
            if relation.project_id == project_id and relation.place_id in requested:
                if self.repository.is_place_used_by_shift(project_id, relation.place_id):
                    raise PlaceRelationConflictError("Project place is used by a shift")
                relation_ids.append(relation.project_place_relation_id)
        return self.repository.bulk_delete_project_place_relations(relation_ids) if relation_ids else 0

    def create_shift_place(self, shift_report_id, place_id, comment, actor):
        if not _shift_allowed(self.repository, shift_report_id, actor):
            raise PlaceRelationForbiddenError("Forbidden")
        context = self.repository.shift_context(shift_report_id)
        if context is None:
            raise PlaceRelationNotFoundError("Shift report not found")
        if not self.repository.has_project_place(context.project_id, place_id):
            raise PlaceRelationConflictError("Place is not linked to shift project")
        if self.repository.has_shift_place(shift_report_id, place_id):
            raise PlaceRelationConflictError("Place is already linked to shift")
        return self.repository.create_shift_place_relation(
            ShiftPlaceRelation(uuid4(), shift_report_id, place_id, comment)
        )

    def bulk_create_shift_places(self, shift_report_id, place_ids, actor):
        if not _shift_allowed(self.repository, shift_report_id, actor):
            raise PlaceRelationForbiddenError("Forbidden")
        context = self.repository.shift_context(shift_report_id)
        if context is None:
            raise PlaceRelationNotFoundError("Shift report not found")
        relations = []
        for place_id in _unique_place_ids(place_ids):
            if not self.repository.has_project_place(context.project_id, place_id):
                raise PlaceRelationConflictError("Place is not linked to shift project")
            if not self.repository.has_shift_place(shift_report_id, place_id):
                relations.append(ShiftPlaceRelation(uuid4(), shift_report_id, place_id, None))
        return self.repository.bulk_create_shift_place_relations(relations) if relations else []

    def update_shift_place(self, relation_id, place_id, comment, actor):
        current = self.repository.get_shift_place_relation(relation_id)
        if current is None:
            raise PlaceRelationNotFoundError("Shift place relation not found")
        _require_shift_mutation(self.repository, current.shift_report_id, actor)
        context = self.repository.shift_context(current.shift_report_id)
        if context is None or not self.repository.has_project_place(context.project_id, place_id):
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
        _require_shift_mutation(self.repository, current.shift_report_id, actor)
        if not self.repository.delete_shift_place_relation(relation_id):
            raise PlaceRelationNotFoundError("Shift place relation not found")

    def bulk_delete_shift_places(self, shift_report_id, place_ids, actor):
        _require_shift_mutation(self.repository, shift_report_id, actor)
        requested = set(_unique_place_ids(place_ids))
        relation_ids = [
            relation.shift_place_relation_id
            for relation in self.repository.list_shift_place_relations()
            if relation.shift_report_id == shift_report_id and relation.place_id in requested
        ]
        return self.repository.bulk_delete_shift_place_relations(relation_ids) if relation_ids else 0
