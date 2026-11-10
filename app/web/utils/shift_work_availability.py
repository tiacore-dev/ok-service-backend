"""Annotate work selection lists with availability for a shift performer."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, TypeVar
from uuid import UUID

from app.adapters.shift_reports import SQLAlchemyShiftWorkAvailabilityReader
from app.use_cases.shift_reports import GetShiftWorkAvailabilityUseCase

T = TypeVar("T")


def with_shift_availability(
    shift_report_id: UUID | None,
    items: Sequence[T],
    work_id_of: Callable[[T], UUID],
    to_response: Callable[[T], dict[str, Any]],
) -> list[dict[str, Any]]:
    """Serialize items, adding availability fields when a shift is given.

    Without `shift_report_id` nothing is looked up and no fields are added.
    """
    responses = [to_response(item) for item in items]
    if shift_report_id is None:
        return responses
    availability = GetShiftWorkAvailabilityUseCase(
        reader=SQLAlchemyShiftWorkAvailabilityReader()
    ).execute(shift_report_id, {work_id_of(item) for item in items})
    for item, response in zip(items, responses):
        state = availability[work_id_of(item)]
        response["available"] = state.available
        response["unavailable_reason"] = state.reason
    return responses
