from dataclasses import dataclass
from uuid import UUID

from .errors import MeasurementUnitValidationError


@dataclass(frozen=True, slots=True)
class MeasurementUnit:
    measurement_unit_id: UUID
    name: str
    created_at: int
    created_by: UUID | None = None

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        if not name:
            raise MeasurementUnitValidationError("Measurement unit name is required.")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "created_at", int(self.created_at))
