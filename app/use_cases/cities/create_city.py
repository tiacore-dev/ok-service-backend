from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.domain.cities import City, CityAlreadyExistsError

from .dto import CreateCityCommand
from .ports import CityRepository
from ..time_utils import utc_epoch_seconds


@dataclass(slots=True)
class CreateCityUseCase:
    repository: CityRepository

    def execute(self, command: CreateCityCommand) -> City:
        if self.repository.get_city_by_name(command.name) is not None:
            raise CityAlreadyExistsError("City already exists")
        city = City(
            city_id=uuid4(),
            name=command.name,
            created_by=command.created_by,
            created_at=utc_epoch_seconds(),
            deleted=False,
        )
        return self.repository.create_city(city)
