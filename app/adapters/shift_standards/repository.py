from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.adapters._typing import normalize_result, require_uuid
from app.database.managers.works_managers import ShiftStandardsManager
from app.domain.shift_standards import ShiftStandard
from app.use_cases.shift_standards.dto import ShiftStandardListQuery


def _entity(payload: dict[str, Any] | None) -> ShiftStandard:
    if payload is None:
        raise ValueError("Shift standard repository returned no record")
    return ShiftStandard(
        shift_standard_id=require_uuid(payload["shift_standard_id"], "shift_standard_id"),
        category=int(payload["category"]),
        standard=float(payload["standard"]),
        notification_text=payload.get("notification_text"),
        created_at=int(payload["created_at"]),
        created_by=require_uuid(payload["created_by"], "created_by"),
    )


@dataclass(slots=True)
class SQLAlchemyShiftStandardRepository:
    manager: ShiftStandardsManager = field(default_factory=ShiftStandardsManager)

    def create_shift_standard(self, item: ShiftStandard) -> ShiftStandard:
        return _entity(
            normalize_result(
                self.manager.add(
                    shift_standard_id=item.shift_standard_id,
                    category=item.category,
                    standard=item.standard,
                    notification_text=item.notification_text,
                    created_at=item.created_at,
                    created_by=item.created_by,
                )
            )
        )

    def get_shift_standard(self, item_id: UUID) -> ShiftStandard | None:
        record = normalize_result(self.manager.get_by_id(item_id))
        return _entity(record) if record else None

    def update_shift_standard(self, item: ShiftStandard) -> ShiftStandard | None:
        record = normalize_result(
            self.manager.update_shift_standard(
                item.shift_standard_id,
                category=item.category,
                standard=item.standard,
                notification_text=item.notification_text,
            )
        )
        return _entity(record) if record else None

    def delete_shift_standard(self, item_id: UUID) -> bool:
        return self.manager.delete(item_id) is not None

    def list_shift_standards(self, query: ShiftStandardListQuery) -> list[ShiftStandard]:
        records = self.manager.get_all_filtered(
            offset=query.offset,
            limit=query.limit,
            category=query.category,
            sort_by="category",
            sort_order="asc",
        )
        return [_entity(record) for record in records]
