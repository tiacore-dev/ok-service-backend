from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.work_prices import WorkPriceNotFoundError

from .ports import WorkPriceRepository


@dataclass(slots=True)
class DeleteWorkPriceUseCase:
    repository: WorkPriceRepository

    def execute(self, work_price_id: UUID) -> bool:
        deleted = self.repository.delete_work_price(work_price_id)
        if not deleted:
            raise WorkPriceNotFoundError("Work price not found")
        return deleted
