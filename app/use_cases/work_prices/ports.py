from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.work_prices import WorkPrice

from .dto import WorkPriceListQuery


class WorkPriceRepository(Protocol):
    def create_work_price(self, work_price: WorkPrice) -> WorkPrice: ...

    def get_work_price(self, work_price_id: UUID) -> WorkPrice | None: ...

    def update_work_price(self, work_price: WorkPrice) -> WorkPrice | None: ...

    def delete_work_price(self, work_price_id: UUID) -> bool: ...

    def list_work_prices(self, query: WorkPriceListQuery) -> list[WorkPrice]: ...
