from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from app.adapters.objects import object_dict_to_entity
from app.domain.objects import Object, ObjectForbiddenError, ObjectNotFoundError
from app.use_cases.objects import (
    CreateObjectCommand,
    CreateObjectUseCase,
    GetObjectUseCase,
    HardDeleteObjectUseCase,
    ListObjectsUseCase,
    ObjectActor,
    ObjectListQuery,
    SoftDeleteObjectUseCase,
    UpdateObjectCommand,
    UpdateObjectUseCase,
)


@dataclass
class FakeObjectRepository:
    obj: Object | None = None
    created: Object | None = None
    updated: Object | None = None
    deleted: UUID | None = None
    listed_query: ObjectListQuery | None = None
    listed_actor: ObjectActor | None = None
    project_statuses: list[str] | None = None

    def get_object_stats(self, object_id: UUID) -> dict[str, object]:
        return {"total": {}, "projects": []}

    def create_object(self, obj: Object) -> Object:
        self.created = obj
        self.obj = obj
        return obj

    def get_object(self, object_id: UUID) -> Object | None:
        return self.obj if self.obj and self.obj.object_id == object_id else None

    def update_object(self, obj: Object) -> Object | None:
        self.updated = obj
        self.obj = obj
        return obj

    def update_object_with_projects_closed(self, obj: Object) -> Object | None:
        if self.obj is None:
            return None
        if any(status != "closed" for status in self.project_statuses or []):
            raise ValueError(
                "Object can be completed only when all its projects are closed"
            )
        return self.update_object(obj)

    def delete_object(self, object_id: UUID) -> bool:
        self.deleted = object_id
        return self.obj is not None and self.obj.object_id == object_id

    def list_objects(self, query: ObjectListQuery, actor: ObjectActor) -> list[Object]:
        self.listed_query = query
        self.listed_actor = actor
        return [self.obj] if self.obj is not None else []

    def get_project_statuses(self, object_id: UUID) -> list[str]:
        return self.project_statuses or []


def _object(*, status: str = "active") -> Object:
    return Object(
        object_id=uuid4(),
        name="Object",
        address="Address",
        description="Description",
        city_id=uuid4(),
        status=status,
        manager=uuid4(),
        lng=10.0,
        ltd=20.0,
        created_by=uuid4(),
        created_at=1,
        deleted=False,
    )


def test_update_object_rejects_completion_when_project_is_not_closed():
    obj = _object(status="active")
    repository = FakeObjectRepository(obj=obj, project_statuses=["in_progress"])

    with pytest.raises(ValueError, match="all its projects are closed"):
        UpdateObjectUseCase(repository).execute(
            UpdateObjectCommand(object_id=obj.object_id, status="completed"),
            ObjectActor(role="admin", user_id=uuid4()),
        )


def test_update_object_allows_completion_when_all_projects_are_closed():
    obj = _object(status="active")
    repository = FakeObjectRepository(obj=obj, project_statuses=["closed", "closed"])

    result = UpdateObjectUseCase(repository).execute(
        UpdateObjectCommand(object_id=obj.object_id, status="completed"),
        ObjectActor(role="admin", user_id=uuid4()),
    )

    assert result.status == "completed"


def test_create_object_use_case_sets_created_by_from_actor():
    repository = FakeObjectRepository()
    actor = ObjectActor(role="admin", user_id=uuid4())
    command = CreateObjectCommand(
        name="New object",
        city=uuid4(),
        created_by=uuid4(),
    )

    result = CreateObjectUseCase(repository=repository).execute(command, actor)

    assert result == repository.created
    assert result.created_by == command.created_by


def test_get_object_use_case_allows_user_to_view_inactive_object():
    repository = FakeObjectRepository(obj=_object(status="inactive"))
    actor = ObjectActor(role="user", user_id=uuid4())

    result = GetObjectUseCase(repository=repository).execute(repository.obj.object_id, actor)  # type: ignore[union-attr]

    assert result == repository.obj


def test_get_object_use_case_returns_object_for_admin():
    obj = _object(status="inactive")
    repository = FakeObjectRepository(obj=obj)
    actor = ObjectActor(role="admin", user_id=uuid4())

    result = GetObjectUseCase(repository=repository).execute(obj.object_id, actor)

    assert result == obj


def test_update_object_use_case_updates_object():
    obj = _object()
    repository = FakeObjectRepository(obj=obj)
    actor = ObjectActor(role="admin", user_id=uuid4())

    result = UpdateObjectUseCase(repository=repository).execute(
        UpdateObjectCommand(object_id=obj.object_id, name="Updated"),
        actor,
    )

    assert result.name == "Updated"
    assert repository.updated is not None


def test_soft_delete_object_use_case_marks_deleted():
    obj = _object()
    repository = FakeObjectRepository(obj=obj)
    actor = ObjectActor(role="admin", user_id=uuid4())

    result = SoftDeleteObjectUseCase(repository=repository).execute(obj.object_id, actor)

    assert result is True
    assert repository.updated is not None
    assert repository.updated.deleted is True


def test_hard_delete_object_use_case_rejects_missing_object():
    repository = FakeObjectRepository()
    actor = ObjectActor(role="admin", user_id=uuid4())

    with pytest.raises(ObjectNotFoundError):
        HardDeleteObjectUseCase(repository=repository).execute(uuid4(), actor)


def test_list_objects_use_case_delegates():
    obj = _object()
    repository = FakeObjectRepository(obj=obj)
    query = ObjectListQuery(name="Object")
    actor = ObjectActor(role="manager", user_id=uuid4())

    result = ListObjectsUseCase(repository=repository).execute(query, actor)

    assert result == [obj]
    assert repository.listed_query == query
    assert repository.listed_actor == actor


def test_list_objects_use_case_allows_user():
    repository = FakeObjectRepository(obj=_object())
    result = ListObjectsUseCase(repository=repository).execute(
        ObjectListQuery(), ObjectActor(role="user", user_id=uuid4())
    )

    assert result == [repository.obj]


def test_object_mapper_treats_string_none_as_missing_created_by():
    obj = object_dict_to_entity(
        {
            "object_id": str(uuid4()),
            "name": "Mapped",
            "address": None,
            "description": None,
            "city": None,
            "status": "active",
            "manager": None,
            "lng": None,
            "ltd": None,
            "created_by": "None",
            "created_at": 1,
            "deleted": False,
        }
    )

    assert obj.created_by is None
