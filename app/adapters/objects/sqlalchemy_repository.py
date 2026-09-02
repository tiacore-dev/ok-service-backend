from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
from app.database.managers.objects_managers import ObjectsManager
from app.database.managers.projects_managers import ProjectsManager
from app.domain.objects import Object
from app.use_cases.objects.dto import ObjectActor, ObjectListQuery
from app.use_cases.objects.ports import ObjectRepository

from .mappers import object_dict_to_entity, object_entity_to_create_payload


@dataclass(slots=True)
class SQLAlchemyObjectRepository(ObjectRepository):
    manager: ObjectsManager = field(default_factory=ObjectsManager)
    projects_manager: ProjectsManager = field(default_factory=ProjectsManager)

    def create_object(self, obj: Object) -> Object:
        created = self.manager.add(**object_entity_to_create_payload(obj))
        record = normalize_result(created)
        if record is None:
            raise ValueError("Object creation did not return a record")
        return object_dict_to_entity(record)

    def get_object(self, object_id: UUID) -> Object | None:
        record = normalize_result(self.manager.get_by_id(object_id))
        if record is None:
            return None
        return object_dict_to_entity(record)

    def update_object(self, obj: Object) -> Object | None:
        updated = self.manager.update(
            record_id=obj.object_id,
            name=obj.name,
            address=obj.address,
            description=obj.description,
            city_id=obj.city_id,
            status=obj.status,
            manager=obj.manager,
            lng=obj.lng,
            ltd=obj.ltd,
            deleted=obj.deleted,
        )
        record = normalize_result(updated)
        if record is None:
            return None
        return object_dict_to_entity(record)

    def delete_object(self, object_id: UUID) -> bool:
        deleted = self.manager.delete(record_id=object_id)
        return deleted is not None

    def list_objects(self, query: ObjectListQuery, actor: ObjectActor) -> list[Object]:
        if query.sort_by is None:
            records = self.manager.get_all_filtered(
                offset=query.offset,
                limit=query.limit,
                sort_order=query.sort_order,
                address=query.address,
                status=query.status,
                name=query.name,
                manager=query.manager,
                deleted=query.deleted,
                city_id=query.city,
                lng=query.lng,
                ltd=query.ltd,
                created_by=query.created_by,
                created_at=query.created_at,
            )
        else:
            records = self.manager.get_all_filtered(
                offset=query.offset,
                limit=query.limit,
                sort_by=query.sort_by,
                sort_order=query.sort_order,
                address=query.address,
                status=query.status,
                name=query.name,
                manager=query.manager,
                deleted=query.deleted,
                city_id=query.city,
                lng=query.lng,
                ltd=query.ltd,
                created_by=query.created_by,
                created_at=query.created_at,
            )
        return [object_dict_to_entity(record) for record in records]

    def update_object_with_projects_closed(self, obj: Object) -> Object | None:
        updated = self.manager.update_with_projects_closed(
            record_id=obj.object_id,
            name=obj.name,
            address=obj.address,
            description=obj.description,
            city_id=obj.city_id,
            status=obj.status,
            manager=obj.manager,
            lng=obj.lng,
            ltd=obj.ltd,
            deleted=obj.deleted,
        )
        record = normalize_result(updated)
        return object_dict_to_entity(record) if record is not None else None

    def get_object_stats(self, object_id: UUID) -> dict[str, object]:
        return self.projects_manager.get_object_stats(object_id)

    def get_object_stats_details(self, object_id: UUID) -> dict[str, object]:
        return self.projects_manager.get_object_stats_details(object_id)
