from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
from app.adapters.statistics import (
    ProjectMaterialStatistics,
    merge_material_stats,
    summarize_material_stats,
)
from app.database.managers.objects_managers import ObjectsManager
from app.database.managers.projects_managers import ProjectsManager
from app.domain.objects import Object
from app.use_cases.objects.dto import ObjectActor, ObjectListQuery, ObjectStatsListQuery
from app.use_cases.objects.ports import ObjectRepository

from .mappers import object_dict_to_entity, object_entity_to_create_payload


@dataclass(slots=True)
class SQLAlchemyObjectRepository(ObjectRepository):
    manager: ObjectsManager = field(default_factory=ObjectsManager)
    projects_manager: ProjectsManager = field(default_factory=ProjectsManager)
    material_statistics: ProjectMaterialStatistics | None = None

    def _project_material_stats(self, project_id: UUID) -> dict[str, dict[str, object]]:
        if self.material_statistics is None:
            return {}
        return self.material_statistics.get_project_material_stats(project_id)

    def _add_material_statistics(
        self, payload: dict[str, object], *, detailed: bool
    ) -> dict[str, object]:
        material_totals: dict[str, dict[str, object]] = {}
        material_summary = {
            "project_material_quantity": 0.0,
            "project_material_summ": 0.0,
            "shift_report_material_quantity": 0.0,
            "shift_report_material_summ_by_estimate": 0.0,
        }
        projects = payload.get("projects", [])
        if not isinstance(projects, list):
            return payload
        for project in projects:
            if not isinstance(project, dict):
                continue
            material_stats = self._project_material_stats(UUID(str(project["project_id"])))
            project["material_stats"] = material_stats
            if detailed:
                merge_material_stats(material_totals, material_stats)
            else:
                for field, value in summarize_material_stats(material_stats).items():
                    material_summary[field] += value
        payload["material_totals"] = material_totals if detailed else material_summary
        return payload

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
            contract_start_date=obj.contract_start_date,
            contract_end_date=obj.contract_end_date,
            order_number=obj.order_number,
            monthly_ks_closing_date=obj.monthly_ks_closing_date,
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
                order_number=query.order_number,
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
                order_number=query.order_number,
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
            contract_start_date=obj.contract_start_date,
            contract_end_date=obj.contract_end_date,
            order_number=obj.order_number,
            monthly_ks_closing_date=obj.monthly_ks_closing_date,
            deleted=obj.deleted,
        )
        record = normalize_result(updated)
        return object_dict_to_entity(record) if record is not None else None

    def get_object_stats(self, object_id: UUID) -> dict[str, object]:
        return self._add_material_statistics(
            self.projects_manager.get_object_stats(object_id), detailed=False
        )

    def get_object_stats_details(self, object_id: UUID) -> dict[str, object]:
        return self._add_material_statistics(
            self.projects_manager.get_object_stats_details(object_id), detailed=True
        )

    def get_all_objects_stats(self, query: ObjectStatsListQuery) -> dict[str, object]:
        payload = self.projects_manager.get_all_objects_stats(
            offset=query.offset, limit=query.limit, search=query.search
        )
        total_summary = {
            "project_material_quantity": 0.0,
            "project_material_summ": 0.0,
            "shift_report_material_quantity": 0.0,
            "shift_report_material_summ_by_estimate": 0.0,
        }
        all_object_ids = payload.pop("_all_object_ids", [])
        objects = payload.get("objects", [])
        if not isinstance(objects, list):
            return payload
        material_by_object: dict[UUID, dict[str, dict[str, object]]] = {}
        for object_id_raw in all_object_ids:
            object_id = UUID(str(object_id_raw))
            material_stats: dict[str, dict[str, object]] = {}
            for project_id in self.projects_manager.get_active_project_ids_by_object(
                object_id
            ):
                merge_material_stats(material_stats, self._project_material_stats(project_id))
            material_by_object[object_id] = material_stats
            for field, value in summarize_material_stats(material_stats).items():
                total_summary[field] += value
        for item in objects:
            if not isinstance(item, dict):
                continue
            material_stats = material_by_object.get(
                UUID(str(item["object_id"])), {}
            )
            item["material_totals"] = summarize_material_stats(material_stats)
        payload["material_totals"] = total_summary
        return payload
