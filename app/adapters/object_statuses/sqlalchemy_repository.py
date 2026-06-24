from __future__ import annotations

from dataclasses import dataclass, field

from app.adapters._typing import normalize_result
from app.database.managers.objects_managers import ObjectStatusesManager
from app.domain.object_statuses import ObjectStatus
from app.use_cases.object_statuses.dto import ObjectStatusListQuery
from app.use_cases.object_statuses.ports import ObjectStatusRepository

from .mappers import object_status_dict_to_entity


@dataclass(slots=True)
class SQLAlchemyObjectStatusRepository(ObjectStatusRepository):
    manager: ObjectStatusesManager = field(default_factory=ObjectStatusesManager)

    def list_object_statuses(self, query: ObjectStatusListQuery) -> list[ObjectStatus]:
        if query.sort_by is None:
            records = self.manager.get_all_filtered(
                offset=query.offset,
                limit=query.limit,
                sort_order=query.sort_order,
                object_status_id=query.object_status_id,
                name=query.name,
            )
        else:
            records = self.manager.get_all_filtered(
                offset=query.offset,
                limit=query.limit,
                sort_by=query.sort_by,
                sort_order=query.sort_order,
                object_status_id=query.object_status_id,
                name=query.name,
            )
        normalized = [normalize_result(record) for record in records]
        return [object_status_dict_to_entity(record) for record in normalized if record is not None]
