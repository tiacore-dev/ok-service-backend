from __future__ import annotations

from dataclasses import dataclass

from app.domain.work_prices import (
    WorkPrice,
    WorkPriceNotFoundError,
    validate_work_price_category,
)

from .dto import UpdateWorkPriceCommand
from .ports import WorkPriceRepository


@dataclass(slots=True)
class UpdateWorkPriceUseCase:
    repository: WorkPriceRepository

    def execute(self, command: UpdateWorkPriceCommand) -> WorkPrice:
        current = self.repository.get_work_price(command.work_price_id)
        if current is None:
            raise WorkPriceNotFoundError("Work price not found")

        changes: dict[str, object] = {}
        if command.work is not None:
            changes["work"] = command.work
        if command.category is not None:
            validate_work_price_category(command.category)
            changes["category"] = command.category
        if command.price is not None:
            changes["price"] = command.price
        if command.deleted is not None:
            changes["deleted"] = command.deleted

        if not changes:
            return current

        updated = current.with_updates(**changes)
        result = self.repository.update_work_price(updated)
        if result is None:
            raise WorkPriceNotFoundError("Work price not found")
        return result
