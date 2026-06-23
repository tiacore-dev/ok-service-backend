from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.database.time_utils import utc_epoch_seconds
from app.domain.work_prices import WorkPrice, validate_work_price_category

from .dto import CreateWorkPriceCommand
from .ports import WorkPriceRepository


@dataclass(slots=True)
class CreateWorkPriceUseCase:
    repository: WorkPriceRepository

    def execute(self, command: CreateWorkPriceCommand) -> WorkPrice:
        validate_work_price_category(command.category)
        work_price = WorkPrice(
            work_price_id=uuid4(),
            work=command.work,
            category=command.category,
            price=command.price,
            created_by=command.created_by,
            created_at=utc_epoch_seconds(),
            deleted=False,
        )
        return self.repository.create_work_price(work_price)
