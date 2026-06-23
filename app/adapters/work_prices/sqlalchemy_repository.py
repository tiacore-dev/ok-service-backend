from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
from app.database.managers.works_managers import WorkPricesManager
from app.domain.work_prices import WorkPrice
from app.use_cases.work_prices.dto import WorkPriceListQuery
from app.use_cases.work_prices.ports import WorkPriceRepository

from .mappers import work_price_dict_to_entity, work_price_entity_to_create_payload


@dataclass(slots=True)
class SQLAlchemyWorkPriceRepository(WorkPriceRepository):
    manager: WorkPricesManager = field(default_factory=WorkPricesManager)

    def create_work_price(self, work_price: WorkPrice) -> WorkPrice:
        created = self.manager.add(**work_price_entity_to_create_payload(work_price))
        record = normalize_result(created)
        if record is None:
            raise ValueError("Work price creation did not return a record")
        return work_price_dict_to_entity(record)

    def get_work_price(self, work_price_id: UUID) -> WorkPrice | None:
        record = normalize_result(self.manager.get_by_id(work_price_id))
        if record is None:
            return None
        return work_price_dict_to_entity(record)

    def update_work_price(self, work_price: WorkPrice) -> WorkPrice | None:
        updated = self.manager.update(
            record_id=work_price.work_price_id,
            work=work_price.work,
            category=work_price.category,
            price=work_price.price,
            deleted=work_price.deleted,
        )
        record = normalize_result(updated)
        if record is None:
            return None
        return work_price_dict_to_entity(record)

    def delete_work_price(self, work_price_id: UUID) -> bool:
        deleted = self.manager.delete(work_price_id)
        return deleted is not None

    def list_work_prices(self, query: WorkPriceListQuery) -> list[WorkPrice]:
        records = self.manager.get_all_filtered(
            offset=query.offset,
            limit=query.limit,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            work=query.work,
            category=query.category,
            price=query.price,
            created_by=query.created_by,
            created_at=query.created_at,
            deleted=query.deleted,
        )
        return [work_price_dict_to_entity(record) for record in records]
