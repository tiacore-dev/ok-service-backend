from __future__ import annotations

from dataclasses import dataclass

from app.domain.leaves import AbsenceReason

from .dto import AbsenceReasonDTO


@dataclass(slots=True)
class ListAbsenceReasonsUseCase:
    def execute(self) -> list[AbsenceReasonDTO]:
        return [
            AbsenceReasonDTO(reason_id=reason.value, name=reason.label())
            for reason in AbsenceReason
        ]

