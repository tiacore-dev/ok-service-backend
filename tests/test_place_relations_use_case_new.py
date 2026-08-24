from uuid import UUID, uuid4

import pytest

from app.use_cases.place_relations import (
    PlaceRelationConflictError,
    PlaceRelationForbiddenError,
    PlaceRelationService,
    ProjectPlaceRelation,
    RelationActor,
    ShiftPlaceRelation,
    ShiftContext,
)


class FakeRepository:
    def __init__(self):
        self.project_id, self.object_id, self.place_id = uuid4(), uuid4(), uuid4()
        self.shift_id, self.user_id, self.leader_id = uuid4(), uuid4(), uuid4()
        self.shift_signed = False
        self.project_relations = {}
        self.shift_relations = {}
    def get_project_place_relation(self, relation_id): return self.project_relations.get(relation_id)
    def create_project_place_relation(self, relation): self.project_relations[relation.project_place_relation_id] = relation; return relation
    def update_project_place_relation(self, relation): self.project_relations[relation.project_place_relation_id] = relation; return relation
    def delete_project_place_relation(self, relation_id): return self.project_relations.pop(relation_id, None) is not None
    def list_project_place_relations(self): return list(self.project_relations.values())
    def get_shift_place_relation(self, relation_id): return self.shift_relations.get(relation_id)
    def create_shift_place_relation(self, relation): self.shift_relations[relation.shift_place_relation_id] = relation; return relation
    def update_shift_place_relation(self, relation): self.shift_relations[relation.shift_place_relation_id] = relation; return relation
    def delete_shift_place_relation(self, relation_id): return self.shift_relations.pop(relation_id, None) is not None
    def list_shift_place_relations(self): return list(self.shift_relations.values())
    def project_object_id(self, project_id): return self.object_id if project_id == self.project_id else None
    def place_object_id(self, place_id): return self.object_id if place_id == self.place_id else None
    def project_leader_id(self, project_id): return self.leader_id if project_id == self.project_id else None
    def shift_context(self, shift_report_id): return ShiftContext(self.project_id, self.user_id, self.shift_signed) if shift_report_id == self.shift_id else None
    def has_project_place(self, project_id, place_id): return any(x.project_id == project_id and x.place_id == place_id for x in self.project_relations.values())
    def has_shift_place(self, shift_report_id, place_id): return any(x.shift_report_id == shift_report_id and x.place_id == place_id for x in self.shift_relations.values())
    def is_place_used_by_shift(self, project_id, place_id): return bool(self.shift_relations) and self.has_project_place(project_id, place_id)
    def bulk_create_project_place_relations(self, relations):
        for relation in relations: self.create_project_place_relation(relation)
        return relations
    def bulk_delete_project_place_relations(self, relation_ids):
        return sum(self.delete_project_place_relation(relation_id) for relation_id in relation_ids)
    def bulk_create_shift_place_relations(self, relations):
        for relation in relations: self.create_shift_place_relation(relation)
        return relations
    def bulk_delete_shift_place_relations(self, relation_ids):
        return sum(self.delete_shift_place_relation(relation_id) for relation_id in relation_ids)


def test_shift_place_requires_project_place_and_allows_assigned_user():
    repo = FakeRepository(); service = PlaceRelationService(repo)
    actor = RelationActor("user", repo.user_id)
    with pytest.raises(PlaceRelationConflictError): service.create_shift_place(repo.shift_id, repo.place_id, None, actor)
    service.create_project_place(repo.project_id, repo.place_id, RelationActor("project-leader", repo.leader_id))
    relation = service.create_shift_place(repo.shift_id, repo.place_id, "ok", actor)
    assert relation.comment == "ok"
    with pytest.raises(PlaceRelationConflictError): service.delete_project_place(next(iter(repo.project_relations)), RelationActor("manager", uuid4()))


def test_project_leader_cannot_manage_another_project():
    repo = FakeRepository()
    with pytest.raises(PlaceRelationForbiddenError):
        PlaceRelationService(repo).create_project_place(repo.project_id, repo.place_id, RelationActor("project-leader", uuid4()))


def test_bulk_project_places_skips_existing_and_deduplicates():
    repo = FakeRepository()
    service = PlaceRelationService(repo)
    actor = RelationActor("admin", uuid4())
    first = service.bulk_create_project_places(repo.project_id, [repo.place_id, repo.place_id], actor)
    second = service.bulk_create_project_places(repo.project_id, [repo.place_id], actor)
    assert len(first) == 1
    assert second == []
    assert service.bulk_delete_project_places(repo.project_id, [repo.place_id, uuid4()], actor) == 1
    assert service.bulk_delete_project_places(repo.project_id, [repo.place_id], actor) == 0


def test_bulk_shift_places_validates_all_before_writing():
    repo = FakeRepository()
    service = PlaceRelationService(repo)
    actor = RelationActor("admin", uuid4())
    service.create_project_place(repo.project_id, repo.place_id, actor)
    with pytest.raises(PlaceRelationConflictError):
        service.bulk_create_shift_places(repo.shift_id, [repo.place_id, uuid4()], actor)
    assert repo.shift_relations == {}


def test_bulk_shift_places_skips_existing_and_missing_on_delete():
    repo = FakeRepository()
    service = PlaceRelationService(repo)
    actor = RelationActor("admin", uuid4())
    service.create_project_place(repo.project_id, repo.place_id, actor)
    created = service.bulk_create_shift_places(repo.shift_id, [repo.place_id, repo.place_id], actor)
    assert len(created) == 1
    assert service.bulk_delete_shift_places(repo.shift_id, [repo.place_id, uuid4()], actor) == 1
    assert service.bulk_delete_shift_places(repo.shift_id, [repo.place_id], actor) == 0


@pytest.mark.parametrize("role", ["manager", "project-leader"])
def test_unassigned_shift_roles_cannot_mutate_shift_places(role):
    repo = FakeRepository()
    actor = RelationActor(role, uuid4())
    with pytest.raises(PlaceRelationForbiddenError):
        PlaceRelationService(repo).create_shift_place(repo.shift_id, repo.place_id, None, actor)


def test_signed_shift_allows_admin_and_assigned_project_leader_only():
    repo = FakeRepository()
    repo.shift_signed = True
    service = PlaceRelationService(repo)
    service.create_project_place(repo.project_id, repo.place_id, RelationActor("admin", uuid4()))

    with pytest.raises(PlaceRelationForbiddenError):
        service.create_shift_place(repo.shift_id, repo.place_id, None, RelationActor("user", repo.user_id))
    relation = service.create_shift_place(
        repo.shift_id, repo.place_id, None,
        RelationActor("project-leader", repo.leader_id),
    )
    with pytest.raises(PlaceRelationForbiddenError):
        service.update_shift_place(relation.shift_place_relation_id, repo.place_id, "edit", RelationActor("user", repo.user_id))


def test_project_place_relations_cannot_be_edited():
    repo = FakeRepository()
    relation = PlaceRelationService(repo).create_project_place(
        repo.project_id, repo.place_id, RelationActor("admin", uuid4())
    )
    with pytest.raises(PlaceRelationForbiddenError):
        PlaceRelationService(repo).update_project_place(
            relation.project_place_relation_id,
            repo.project_id,
            repo.place_id,
            RelationActor("admin", uuid4()),
        )
