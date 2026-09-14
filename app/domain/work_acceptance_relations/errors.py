from decimal import Decimal
from uuid import UUID


class DomainError(Exception):
    """Base error for work acceptance relation domain failures."""


class WorkAcceptanceRelationValidationError(DomainError):
    """Raised when relation data is invalid."""


class WorkAcceptanceQuantityExceededError(DomainError):
    """Raised when accepted quantity exceeds the specification quantity."""

    def __init__(
        self,
        *,
        work_id: UUID,
        specification_quantity: Decimal,
        available_quantity: Decimal,
        requested_quantity: Decimal,
        exceeded_quantity: Decimal,
    ) -> None:
        self.work_id = work_id
        self.specification_quantity = specification_quantity
        self.available_quantity = available_quantity
        self.requested_quantity = requested_quantity
        self.exceeded_quantity = exceeded_quantity
        super().__init__(
            "Work acceptance relation quantity exceeds the available quantity "
            f"for work {work_id}"
        )


class WorkAcceptanceRelationNotFoundError(DomainError):
    """Raised when a relation cannot be found."""
