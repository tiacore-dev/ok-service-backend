from dataclasses import dataclass

from app.domain.object_statuses import ObjectStatus
from app.use_cases.object_statuses import (
    ListObjectStatusesUseCase,
    ObjectStatusListQuery,
)


@dataclass
class FakeObjectStatusRepository:
    statuses: list[ObjectStatus]
    listed_query: ObjectStatusListQuery | None = None

    def list_object_statuses(self, query: ObjectStatusListQuery) -> list[ObjectStatus]:
        self.listed_query = query
        return self.statuses


def test_list_object_statuses_use_case_delegates():
    statuses = [ObjectStatus(object_status_id="active", name="Active")]
    repository = FakeObjectStatusRepository(statuses=statuses)
    query = ObjectStatusListQuery(name="Act")

    result = ListObjectStatusesUseCase(repository=repository).execute(query)

    assert result == statuses
    assert repository.listed_query == query
