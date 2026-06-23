from uuid import uuid4

import pytest

from app.domain.leaves import (
    AbsenceReason,
    Leave,
    LeavePeriod,
    LeaveValidationError,
    leave_periods_overlap,
)


def test_absence_reason_labels_are_stable():
    assert AbsenceReason.VACATION.label() == "Отпуск"
    assert AbsenceReason.SICK_LEAVE.label() == "Больничный"
    assert AbsenceReason.DAY_OFF.label() == "Отгул"


def test_leave_period_overlap_rules():
    assert leave_periods_overlap(20240101, 20240105, 20240105, 20240110) is True
    assert leave_periods_overlap(20240101, 20240105, 20240106, 20240110) is False


def test_leave_entity_enforces_period_invariant():
    leave = Leave(
        leave_id=uuid4(),
        start_date=20240101,
        end_date=20240105,
        reason=AbsenceReason.VACATION,
        user_id=uuid4(),
        responsible_id=uuid4(),
        comment="Trip",
        created_by=uuid4(),
        created_at=1704067200,
    )

    assert isinstance(leave.period, LeavePeriod)
    assert leave.period.start_date == 20240101
    assert leave.period.end_date == 20240105
    assert leave.deleted is False


def test_leave_entity_rejects_invalid_period():
    with pytest.raises(LeaveValidationError):
        Leave(
            leave_id=uuid4(),
            start_date=20240105,
            end_date=20240101,
            reason=AbsenceReason.VACATION,
            user_id=uuid4(),
            responsible_id=uuid4(),
            comment=None,
            created_by=uuid4(),
            created_at=1704067200,
        )
