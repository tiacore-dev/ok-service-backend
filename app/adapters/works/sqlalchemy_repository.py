from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
from app.database.managers.works_managers import WorksManager
from app.domain.works import Work
from app.use_cases.works.dto import WorkListQuery
from app.use_cases.works.ports import WorkRepository

from .mappers import work_dict_to_entity, work_entity_to_create_payload


@dataclass(slots=True)
class SQLAlchemyWorkRepository(WorkRepository):
    manager: WorksManager = field(default_factory=WorksManager)

    def create_work(self, work: Work) -> Work:
        created = self.manager.add(**work_entity_to_create_payload(work))
        record = normalize_result(created)
        if record is None:
            raise ValueError("Work creation did not return a record")
        return work_dict_to_entity(record)

    def get_work(self, work_id: UUID) -> Work | None:
        record = normalize_result(self.manager.get_by_id(work_id))
        if record is None:
            return None
        return work_dict_to_entity(record)

    def update_work(self, work: Work) -> Work | None:
        updated = self.manager.update(
            record_id=work.work_id,
            name=work.name,
            category=work_entity_to_create_payload(work)["category"],
            measurement_unit=work.measurement_unit,
            deleted=work.deleted,
        )
        record = normalize_result(updated)
        if record is None:
            return None
        return work_dict_to_entity(record)

    def delete_work(self, work_id: UUID) -> bool:
        deleted = self.manager.delete(work_id)
        return deleted is not None

    def list_works(self, query: WorkListQuery) -> list[Work]:
        records = self.manager.get_all_filtered(
            offset=query.offset,
            limit=query.limit,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            name=query.name,
            deleted=query.deleted,
        )
        return [work_dict_to_entity(record) for record in records]
