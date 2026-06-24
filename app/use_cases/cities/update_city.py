from __future__ import annotations

from dataclasses import dataclass

from app.domain.cities import City, CityAlreadyExistsError, CityNotFoundError

from .dto import UpdateCityCommand
from .ports import CityRepository


@dataclass(slots=True)
class UpdateCityUseCase:
    repository: CityRepository

    def execute(self, command: UpdateCityCommand) -> City:
        current = self.repository.get_city(command.city_id)
        if current is None:
            raise CityNotFoundError("City not found")

        if not command.has_name and not command.has_deleted:
            return current

        name = current.name
        if command.has_name:
            if command.name is None or not str(command.name).strip():
                raise ValueError("Bad request, invalid data.")
            candidate = str(command.name).strip()
            existing = self.repository.get_city_by_name(candidate)
            if existing is not None and existing.city_id != current.city_id:
                raise CityAlreadyExistsError("City already exists")
            name = candidate

        deleted = current.deleted
        if command.has_deleted:
            if command.deleted is None:
                raise ValueError("Bad request, invalid data.")
            deleted = command.deleted

        updated = current.with_updates(name=name, deleted=deleted)
        result = self.repository.update_city(updated)
        if result is None:
            raise CityNotFoundError("City not found")
        return result
