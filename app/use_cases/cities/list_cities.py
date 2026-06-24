from __future__ import annotations

from dataclasses import dataclass

from app.domain.cities import City

from .dto import CityListQuery
from .ports import CityRepository


@dataclass(slots=True)
class ListCitiesUseCase:
    repository: CityRepository

    def execute(self, query: CityListQuery) -> list[City]:
        return self.repository.list_cities(query)
