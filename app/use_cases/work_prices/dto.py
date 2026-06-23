from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateWorkPriceCommand:
    work: UUID
    category: int
    price: Decimal
    created_by: UUID


@dataclass(frozen=True, slots=True)
class UpdateWorkPriceCommand:
    work_price_id: UUID
    work: UUID | None = None
    category: int | None = None
    price: Decimal | None = None
    deleted: bool | None = None


@dataclass(frozen=True, slots=True)
class WorkPriceListQuery:
    offset: int = 0
    limit: int | None = 1000
    sort_by: str = "created_at"
    sort_order: str = "desc"
    work: UUID | None = None
    category: int | None = None
    price: Decimal | None = None
    created_by: UUID | None = None
    created_at: int | None = None
    deleted: bool | None = None
