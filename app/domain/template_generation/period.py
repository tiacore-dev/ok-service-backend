"""Technical calendar limits shared by report requests and builders."""

from datetime import date, timedelta

MAX_REPORT_PERIOD_END = date.max - timedelta(days=1)


def validate_report_period_end(end: date) -> None:
    # Inclusive periods need a representable midnight after their final day.
    if end > MAX_REPORT_PERIOD_END:
        raise ValueError(
            f"Конец периода должен быть не позднее {MAX_REPORT_PERIOD_END.isoformat()}"
        )
