from dataclasses import dataclass

from .dto import ShiftStandardListQuery
from .ports import ShiftStandardRepository


@dataclass(slots=True)
class ListShiftStandardsUseCase:
    repository: ShiftStandardRepository

    def execute(self, query: ShiftStandardListQuery):
        return self.repository.list_shift_standards(query)
