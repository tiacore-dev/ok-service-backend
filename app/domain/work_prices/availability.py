from __future__ import annotations

from dataclasses import dataclass

from .policies import WORK_UNAVAILABLE_FOR_CATEGORY_MESSAGE


@dataclass(frozen=True, slots=True)
class WorkAvailability:
    """Whether a work type can be added to a shift of a given performer."""

    available: bool
    reason: str | None = None

    @classmethod
    def allowed(cls) -> WorkAvailability:
        return cls(available=True, reason=None)

    @classmethod
    def unavailable_for_category(cls) -> WorkAvailability:
        return cls(available=False, reason=WORK_UNAVAILABLE_FOR_CATEGORY_MESSAGE)
