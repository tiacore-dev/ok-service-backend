from __future__ import annotations

from dataclasses import dataclass

from .dto import WorkPriceListQuery
from .ports import WorkPriceRepository


@dataclass(slots=True)
class ListWorkPricesUseCase:
    repository: WorkPriceRepository

    def execute(self, query: WorkPriceListQuery):
        return self.repository.list_work_price_records(query)
