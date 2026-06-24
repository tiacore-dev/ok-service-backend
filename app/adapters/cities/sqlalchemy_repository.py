from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
from app.database.managers.cities_manager import CitiesManager
from app.domain.cities import City
from app.use_cases.cities.dto import CityListQuery
from app.use_cases.cities.ports import CityRepository

from .mappers import city_dict_to_entity, city_entity_to_create_payload


@dataclass(slots=True)
class SQLAlchemyCityRepository(CityRepository):
    manager: CitiesManager = field(default_factory=CitiesManager)

    def create_city(self, city: City) -> City:
        created = self.manager.add(**city_entity_to_create_payload(city))
        record = normalize_result(created)
        if record is None:
            raise ValueError("City creation did not return a record")
        return city_dict_to_entity(record)

    def get_city(self, city_id: UUID) -> City | None:
        record = normalize_result(self.manager.get_by_id(city_id))
        if record is None:
            return None
        return city_dict_to_entity(record)

    def get_city_by_name(self, name: str) -> City | None:
        record = normalize_result(self.manager.filter_one_by_dict(name=name))
        if record is None:
            return None
        return city_dict_to_entity(record)

    def update_city(self, city: City) -> City | None:
        updated = self.manager.update(
            record_id=city.city_id,
            name=city.name,
            deleted=city.deleted,
        )
        record = normalize_result(updated)
        if record is None:
            return None
        return city_dict_to_entity(record)

    def delete_city(self, city_id: UUID) -> bool:
        deleted = self.manager.delete(record_id=city_id)
        return deleted is not None

    def list_cities(self, query: CityListQuery) -> list[City]:
        if query.sort_by is None:
            records = self.manager.get_all_filtered(
                offset=query.offset,
                limit=query.limit,
                sort_order=query.sort_order,
                name=query.name,
                deleted=query.deleted,
            )
        else:
            records = self.manager.get_all_filtered(
                offset=query.offset,
                limit=query.limit,
                sort_by=query.sort_by,
                sort_order=query.sort_order,
                name=query.name,
                deleted=query.deleted,
            )
        return [city_dict_to_entity(record) for record in records]
