from decimal import Decimal
from uuid import uuid4

from app.domain.work_prices import WorkPrice
from app.use_cases.work_prices import (
    CreateWorkPriceCommand,
    CreateWorkPriceUseCase,
    UpdateWorkPriceCommand,
    UpdateWorkPriceUseCase,
)


class FakeWorkPriceRepository:
    def __init__(self, work_price: WorkPrice | None = None):
        self.work_price = work_price
        self.created = None
        self.updated = None

    def create_work_price(self, work_price: WorkPrice) -> WorkPrice:
        self.created = work_price
        self.work_price = work_price
        return work_price

    def get_work_price(self, work_price_id):
        if self.work_price and self.work_price.work_price_id == work_price_id:
            return self.work_price
        return None

    def update_work_price(self, work_price: WorkPrice):
        self.updated = work_price
        self.work_price = work_price
        return work_price

    def delete_work_price(self, work_price_id):
        return self.work_price is not None and self.work_price.work_price_id == work_price_id

    def list_work_prices(self, query):
        return [self.work_price] if self.work_price is not None else []


def test_create_work_price_use_case():
    repository = FakeWorkPriceRepository()
    command = CreateWorkPriceCommand(
        work=uuid4(),
        category=1,
        price=Decimal("123.45"),
        created_by=uuid4(),
    )

    result = CreateWorkPriceUseCase(repository=repository).execute(command)

    assert result == repository.created
    assert result.deleted is False
    assert result.category == 1


def test_update_work_price_use_case():
    work_price = WorkPrice(
        work_price_id=uuid4(),
        work=uuid4(),
        category=1,
        price=Decimal("100.00"),
        created_by=uuid4(),
        created_at=1,
    )
    repository = FakeWorkPriceRepository(work_price)

    result = UpdateWorkPriceUseCase(repository=repository).execute(
        UpdateWorkPriceCommand(
            work_price_id=work_price.work_price_id,
            price=Decimal("150.00"),
            deleted=True,
        )
    )

    assert result.price == Decimal("150.00")
    assert result.deleted is True
