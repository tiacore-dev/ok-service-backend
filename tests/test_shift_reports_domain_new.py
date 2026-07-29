from decimal import Decimal
from uuid import uuid4

import pytest

from app.adapters.shift_reports.mappers import shift_report_dict_to_entity
from app.domain.shift_reports import (
    ShiftReport,
    ShiftReportDetail,
    ShiftReportValidationError,
)


def test_shift_report_rejects_negative_date():
    with pytest.raises(ShiftReportValidationError):
        ShiftReport(
            shift_report_id=uuid4(),
            user=uuid4(),
            date=-1,
            date_start=None,
            date_end=None,
            project=uuid4(),
            lng_start=None,
            ltd_start=None,
            lng_end=None,
            ltd_end=None,
            distance_start=None,
            distance_end=None,
            signed=False,
            deleted=False,
            created_by=uuid4(),
            created_at=1,
            night_shift=False,
            extreme_conditions=False,
            number=1,
        )


def test_shift_report_detail_rejects_negative_quantity():
    with pytest.raises(ShiftReportValidationError):
        ShiftReportDetail(
            shift_report_detail_id=uuid4(),
            shift_report=uuid4(),
            project_work=None,
            work=uuid4(),
            quantity=Decimal("-1"),
            summ=Decimal("0"),
            created_by=uuid4(),
            created_at=1,
        )


def test_shift_report_mapper_reads_legacy_inconsistent_time_range():
    payload = {
        "shift_report_id": uuid4(),
        "user": uuid4(),
        "date": 1,
        "date_start": 1_800_000_000,
        "date_end": 1_700_000_000,
        "project": uuid4(),
        "created_by": uuid4(),
        "created_at": 1,
        "number": 1,
    }

    report = shift_report_dict_to_entity(payload)

    assert report.date_start == 1_800_000_000
    assert report.date_end == 1_700_000_000
