from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from app.domain.cities import City, CityAlreadyExistsError, CityNotFoundError
from app.use_cases.cities import (
    CityListQuery,
    CreateCityCommand,
    CreateCityUseCase,
    HardDeleteCityUseCase,
    ListCitiesUseCase,
    SoftDeleteCityUseCase,
    UpdateCityCommand,
    UpdateCityUseCase,
)


@dataclass
class FakeCityRepository:
    city: City | None = None
    city_by_name: City | None = None
    created: City | None = None
    updated: City | None = None
    deleted: UUID | None = None
    listed_query: CityListQuery | None = None

    def create_city(self, city: City) -> City:
        self.created = city
        self.city = city
        return city

    def get_city(self, city_id: UUID) -> City | None:
        return self.city if self.city and self.city.city_id == city_id else None

    def get_city_by_name(self, name: str) -> City | None:
        return self.city_by_name if self.city_by_name and self.city_by_name.name == name else None

    def update_city(self, city: City) -> City | None:
        self.updated = city
        self.city = city
        return city

    def delete_city(self, city_id: UUID) -> bool:
        self.deleted = city_id
        return self.city is not None and self.city.city_id == city_id

    def list_cities(self, query: CityListQuery) -> list[City]:
        self.listed_query = query
        return [self.city] if self.city is not None else []


def _city() -> City:
    return City(
        city_id=uuid4(),
        name="Novosibirsk",
        created_by=uuid4(),
        created_at=1,
        deleted=False,
    )


def test_create_city_use_case():
    repository = FakeCityRepository()
    command = CreateCityCommand(name="Tomsk", created_by=uuid4())

    result = CreateCityUseCase(repository=repository).execute(command)

    assert result == repository.created
    assert result.name == "Tomsk"


def test_create_city_use_case_rejects_duplicate_name():
    city = _city()
    repository = FakeCityRepository(city_by_name=city)

    with pytest.raises(CityAlreadyExistsError):
        CreateCityUseCase(repository=repository).execute(
            CreateCityCommand(name=city.name, created_by=uuid4())
        )


def test_update_city_use_case_updates_name():
    city = _city()
    repository = FakeCityRepository(city=city)

    result = UpdateCityUseCase(repository=repository).execute(
        UpdateCityCommand(city_id=city.city_id, has_name=True, name="Omsk")
    )

    assert result.name == "Omsk"
    assert repository.updated is not None


def test_update_city_use_case_rejects_foreign_duplicate():
    city = _city()
    other_city = _city()
    repository = FakeCityRepository(city=city, city_by_name=other_city)

    with pytest.raises(CityAlreadyExistsError):
        UpdateCityUseCase(repository=repository).execute(
            UpdateCityCommand(city_id=city.city_id, has_name=True, name=other_city.name)
        )


def test_update_city_use_case_requires_data():
    city = _city()
    repository = FakeCityRepository(city=city)

    result = UpdateCityUseCase(repository=repository).execute(
        UpdateCityCommand(city_id=city.city_id)
    )

    assert result == city


def test_soft_delete_city_use_case():
    city = _city()
    repository = FakeCityRepository(city=city)

    result = SoftDeleteCityUseCase(repository=repository).execute(city.city_id)

    assert result is True
    assert repository.updated is not None
    assert repository.updated.deleted is True


def test_hard_delete_city_use_case_requires_existing_record():
    repository = FakeCityRepository()

    with pytest.raises(CityNotFoundError):
        HardDeleteCityUseCase(repository=repository).execute(uuid4())


def test_list_cities_use_case_delegates():
    city = _city()
    repository = FakeCityRepository(city=city)
    query = CityListQuery(name="Novo")

    result = ListCitiesUseCase(repository=repository).execute(query)

    assert result == [city]
    assert repository.listed_query == query
