from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.cities import CityNotFoundError

from .ports import CityRepository


@dataclass(slots=True)
class SoftDeleteCityUseCase:
    repository: CityRepository

    def execute(self, city_id: UUID) -> bool:
        city = self.repository.get_city(city_id)
        if city is None:
            raise CityNotFoundError("City not found")
        updated = city.with_updates(deleted=True)
        return self.repository.update_city(updated) is not None


@dataclass(slots=True)
class HardDeleteCityUseCase:
    repository: CityRepository

    def execute(self, city_id: UUID) -> bool:
        if self.repository.get_city(city_id) is None:
            raise CityNotFoundError("City not found")
        return self.repository.delete_city(city_id)
