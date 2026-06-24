from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.cities import City, CityNotFoundError

from .ports import CityRepository


@dataclass(slots=True)
class GetCityUseCase:
    repository: CityRepository

    def execute(self, city_id: UUID) -> City:
        city = self.repository.get_city(city_id)
        if city is None:
            raise CityNotFoundError("City not found")
        return city
