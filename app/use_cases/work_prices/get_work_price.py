from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.work_prices import WorkPriceNotFoundError

from .ports import WorkPriceRepository


@dataclass(slots=True)
class GetWorkPriceUseCase:
    repository: WorkPriceRepository

    def execute(self, work_price_id: UUID):
        record = self.repository.get_work_price_record(work_price_id)
        if record is None:
            raise WorkPriceNotFoundError("Work price not found")
        return record
