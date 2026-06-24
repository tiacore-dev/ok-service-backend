from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.domain.shift_reports import (
    ShiftReport,
    ShiftReportDetail,
    ShiftReportForbiddenError,
)
from app.use_cases.shift_reports import (
    CreateShiftReportCommand,
    CreateShiftReportDetailPayload,
    CreateShiftReportDetailUseCase,
    ShiftReportActor,
    ShiftReportListQuery,
    UpdateShiftReportCommand,
    UpdateShiftReportUseCase,
    CreateShiftReportUseCase,
    ListShiftReportsUseCase,
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
        return self.current.with_updates(deleted=bool(command.deleted))

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


def test_create_shift_report_for_user_forces_actor_identity():
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

    use_case.execute(command, actor)

    assert repository.created_command is not None
    assert repository.created_command.user == actor.user_id
    assert repository.created_command.signed is False


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


def test_list_shift_reports_for_user_forces_own_filter():
    report = _report()
    repository = _FakeRepository(current=report)
    use_case = ListShiftReportsUseCase(repository=repository)
    actor = ShiftReportActor(role="user", user_id=uuid4())
    query = ShiftReportListQuery(user=[uuid4()])

    use_case.execute(query, actor)

    assert repository.listed_filters is not None
    assert repository.listed_filters["user"] is None


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
