from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
import app.use_cases.shift_reports.update_shift_report_time as shift_report_time_module

from app.domain.shift_reports import (
    ShiftReport,
    ShiftReportDetail,
    ShiftReportForbiddenError,
    ShiftReportValidationError,
)
from app.use_cases.shift_reports import (
    CreateShiftReportCommand,
    CreateShiftReportDetailPayload,
    CreateShiftReportDetailUseCase,
    CreateShiftReportUseCase,
    DeleteShiftReportUseCase,
    ListShiftReportsUseCase,
    ShiftReportActor,
    ShiftReportListQuery,
    UpdateShiftReportCommand,
    UpdateShiftReportUseCase,
    UpdateShiftReportTimeUseCase,
    ShiftReportTimeCommand,
    SoftDeleteShiftReportUseCase,
)


@dataclass
class _FakeRepository:
    current: ShiftReport
    detail_result: ShiftReportDetail | None = None
    created_command: CreateShiftReportCommand | None = None
    listed_filters: dict[str, object] | None = field(default=None, init=False)
    project_ids: list[UUID] = field(default_factory=list)

    def get_shift_report(self, shift_report_id):
        return self.current if shift_report_id == self.current.shift_report_id else None

    def update_shift_report(self, command):
        changes = {}
        for field in ("deleted", "date_start", "date_end", "lng_start", "ltd_start", "lng_end", "ltd_end"):
            value = getattr(command, field, None)
            if value is not None:
                changes[field] = value
        return self.current.with_updates(**changes)

    def delete_shift_report(self, shift_report_id):
        return shift_report_id == self.current.shift_report_id

    def create_shift_report_detail(self, command) -> ShiftReportDetail:
        assert self.detail_result is not None
        return self.detail_result

    def create_shift_report(self, command):
        self.created_command = command
        return self.current

    def list_shift_reports(self, **filters):
        self.listed_filters = filters
        return 1, [self.current]

    def get_project_ids_by_leader(self, user_id):
        return self.project_ids

    def get_total_sum_by_shift_report(self, shift_report_id):
        return 0

    def get_project_stats(self, project_id):
        return {}

    def get_shift_report_detail(self, shift_report_detail_id):
        return None

    def update_shift_report_detail(self, command):
        return None

    def delete_shift_report_detail(self, shift_report_detail_id):
        return False

    def list_shift_report_details(self, **filters):
        return []


def _report():
    return ShiftReport(
        shift_report_id=uuid4(),
        user=uuid4(),
        date=1,
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


def _detail(report: ShiftReport) -> ShiftReportDetail:
    return ShiftReportDetail(
        shift_report_detail_id=uuid4(),
        shift_report=report.shift_report_id,
        project_work=None,
        work=uuid4(),
        quantity=Decimal("2.5"),
        summ=Decimal("10.0"),
        created_by=report.created_by,
        created_at=1,
        shift_report_user=report.user,
        shift_report_date=report.date,
        project_work_name=None,
    )


def test_update_shift_report_forbids_foreign_user():
    report = _report()
    repository = _FakeRepository(current=report)
    use_case = UpdateShiftReportUseCase(repository=repository)
    actor = ShiftReportActor(role="user", user_id=uuid4())

    with pytest.raises(ShiftReportForbiddenError):
        use_case.execute(
            UpdateShiftReportCommand(
                shift_report_id=report.shift_report_id, deleted=True
            ),
            actor,
        )


@pytest.mark.parametrize(
    "use_case_class", [SoftDeleteShiftReportUseCase, DeleteShiftReportUseCase]
)
def test_user_cannot_delete_shift_report(use_case_class):
    report = _report()
    repository = _FakeRepository(current=report)
    actor = ShiftReportActor(role="user", user_id=report.user)

    with pytest.raises(ShiftReportForbiddenError, match="cannot delete"):
        use_case_class(repository=repository).execute(report.shift_report_id, actor)


def test_user_cannot_delete_shift_report_through_edit():
    report = _report()
    repository = _FakeRepository(current=report)
    actor = ShiftReportActor(role="user", user_id=report.user)

    with pytest.raises(ShiftReportForbiddenError, match="cannot delete"):
        UpdateShiftReportUseCase(repository=repository).execute(
            UpdateShiftReportCommand(
                shift_report_id=report.shift_report_id, deleted=True
            ),
            actor,
        )


def test_soft_delete_shift_report_marks_deleted():
    report = _report()
    repository = _FakeRepository(current=report)
    use_case = UpdateShiftReportUseCase(repository=repository)
    actor = ShiftReportActor(role="admin", user_id=uuid4())

    updated = use_case.execute(
        UpdateShiftReportCommand(shift_report_id=report.shift_report_id, deleted=True),
        actor,
    )

    assert updated.deleted is True


def test_update_shift_report_sets_audit_user_from_actor():
    report = _report()
    repository = _FakeRepository(current=report)
    use_case = UpdateShiftReportUseCase(repository=repository)
    actor = ShiftReportActor(role="admin", user_id=uuid4())
    captured = {}

    def update(command):
        captured["updated_by"] = command.updated_by
        return report

    repository.update_shift_report = update
    use_case.execute(
        UpdateShiftReportCommand(shift_report_id=report.shift_report_id), actor
    )

    assert captured["updated_by"] == actor.user_id


def test_update_shift_report_allows_manual_lifecycle_correction():
    report = _report()
    repository = _FakeRepository(current=report)
    use_case = UpdateShiftReportUseCase(repository=repository)
    actor = ShiftReportActor(role="admin", user_id=uuid4())

    updated = use_case.execute(
        UpdateShiftReportCommand(
            shift_report_id=report.shift_report_id,
            date_start=1_800_000_000_000,
            date_end=1_800_000_003_000,
            lng_start=82.9,
            ltd_start=55.0,
            lng_end=82.91,
            ltd_end=55.01,
        ),
        actor,
    )

    assert updated.date_start == 1_800_000_000_000
    assert updated.date_end == 1_800_000_003_000
    assert updated.lng_start == 82.9
    assert updated.ltd_start == 55.0
    assert updated.lng_end == 82.91
    assert updated.ltd_end == 55.01


def test_shift_report_time_use_case_rejects_finish_before_start():
    report = _report()
    repository = _FakeRepository(current=report)
    use_case = UpdateShiftReportTimeUseCase(repository=repository)
    actor = ShiftReportActor(role="admin", user_id=uuid4())

    with pytest.raises(Exception, match="has not been started"):
        use_case.finish(
            ShiftReportTimeCommand(report.shift_report_id, actor.user_id, 82.9, 55.0),
            actor,
        )


def test_shift_report_time_use_case_rejects_second_start():
    report = _report().with_updates(date_start=1)
    repository = _FakeRepository(current=report)
    use_case = UpdateShiftReportTimeUseCase(repository=repository)
    actor = ShiftReportActor(role="admin", user_id=uuid4())

    with pytest.raises(Exception, match="already been started"):
        use_case.start(
            ShiftReportTimeCommand(report.shift_report_id, actor.user_id, 82.9, 55.0),
            actor,
        )


def test_shift_report_time_use_case_uses_current_epoch_for_start(monkeypatch):
    report = _report()
    repository = _FakeRepository(current=report)
    use_case = UpdateShiftReportTimeUseCase(repository=repository)
    actor = ShiftReportActor(role="admin", user_id=uuid4())
    expected_timestamp = 1_800_000_000_000

    monkeypatch.setattr(
        shift_report_time_module,
        "utc_epoch_milliseconds",
        lambda: expected_timestamp,
    )

    updated = use_case.start(
        ShiftReportTimeCommand(report.shift_report_id, actor.user_id, 82.9, 55.0),
        actor,
    )

    assert updated.date_start == expected_timestamp


def test_shift_report_time_use_case_rejects_start_when_end_already_exists():
    report = _report().with_updates(date_end=1)
    repository = _FakeRepository(current=report)
    use_case = UpdateShiftReportTimeUseCase(repository=repository)
    actor = ShiftReportActor(role="admin", user_id=uuid4())

    with pytest.raises(Exception, match="end time"):
        use_case.start(
            ShiftReportTimeCommand(report.shift_report_id, actor.user_id, 82.9, 55.0),
            actor,
        )


def test_create_shift_report_detail_calls_repository():
    report = _report()
    repository = _FakeRepository(current=report, detail_result=_detail(report))
    use_case = CreateShiftReportDetailUseCase(repository=repository)
    payload = CreateShiftReportDetailPayload(
        shift_report=report.shift_report_id,
        project_work=None,
        work=uuid4(),
        quantity=Decimal("2.5"),
        created_by=report.created_by,
    )

    assert use_case.execute(payload) is repository.detail_result


def test_create_shift_report_for_user_is_forbidden():
    report = _report()
    repository = _FakeRepository(current=report)
    use_case = CreateShiftReportUseCase(repository=repository)
    actor = ShiftReportActor(role="user", user_id=uuid4())
    command = CreateShiftReportCommand(
        user=uuid4(),
        date=1,
        project=uuid4(),
        signed=True,
    )

    with pytest.raises(ShiftReportForbiddenError, match="cannot create"):
        use_case.execute(command, actor)
    assert repository.created_command is None


def test_create_shift_report_for_admin_keeps_payload_user():
    report = _report()
    repository = _FakeRepository(current=report)
    use_case = CreateShiftReportUseCase(repository=repository)
    actor = ShiftReportActor(role="admin", user_id=uuid4())
    command = CreateShiftReportCommand(
        user=uuid4(),
        date=1,
        project=uuid4(),
        signed=True,
    )

    use_case.execute(command, actor)

    assert repository.created_command is not None
    assert repository.created_command.user == command.user
    assert repository.created_command.signed is True
    assert repository.created_command.created_by == actor.user_id


def test_list_shift_reports_for_user_forces_own_filter():
    report = _report()
    repository = _FakeRepository(current=report)
    use_case = ListShiftReportsUseCase(repository=repository)
    actor = ShiftReportActor(role="user", user_id=uuid4())
    query = ShiftReportListQuery(user=[uuid4()])

    use_case.execute(query, actor)

    assert repository.listed_filters is not None
    assert repository.listed_filters["user"] == [actor.user_id]


def test_list_shift_reports_for_project_leader_without_projects_returns_empty():
    report = _report()
    repository = _FakeRepository(current=report)
    use_case = ListShiftReportsUseCase(repository=repository)
    actor = ShiftReportActor(role="project-leader", user_id=uuid4())
    query = ShiftReportListQuery()

    total, items = use_case.execute(query, actor)

    assert total == 0
    assert items == []
    assert repository.listed_filters is None


def test_list_shift_reports_for_project_leader_forbids_foreign_project():
    report = _report()
    project_id = uuid4()
    repository = _FakeRepository(current=report, project_ids=[uuid4()])
    use_case = ListShiftReportsUseCase(repository=repository)
    actor = ShiftReportActor(role="project-leader", user_id=uuid4())
    query = ShiftReportListQuery(project=[project_id])

    with pytest.raises(ShiftReportForbiddenError):
        use_case.execute(query, actor)
