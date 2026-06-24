from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.cities import City

from .dto import CityListQuery


class CityRepository(Protocol):
    def create_city(self, city: City) -> City: ...

    def get_city(self, city_id: UUID) -> City | None: ...

    def get_city_by_name(self, name: str) -> City | None: ...

    def update_city(self, city: City) -> City | None: ...

    def delete_city(self, city_id: UUID) -> bool: ...

    def list_cities(self, query: CityListQuery) -> list[City]: ...
