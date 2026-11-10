"""Use-case rules for adding/replacing works by the shift performer category."""

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.domain.shift_reports import (
    ShiftReportDetail,
    ShiftReportNotFoundError,
    ShiftReportWorkUnavailableError,
)
from app.use_cases.shift_reports import (
    CreateShiftReportCommand,
    CreateShiftReportDetailCommand,
    CreateShiftReportDetailPayload,
    CreateShiftReportDetailUseCase,
    CreateShiftReportUseCase,
    GetShiftWorkAvailabilityUseCase,
    ShiftReportActor,
    UpdateShiftReportDetailCommand,
    UpdateShiftReportDetailUseCase,
)
from app.use_cases.shift_reports.create_shift_reports import CreateShiftReportsUseCase

MESSAGE = "Работа недоступна для категории исполнителя"


@dataclass
class _Repository:
    """In-memory port: prices[(work, category)] and performer categories."""

    prices: dict[tuple[UUID, int], Decimal] = field(default_factory=dict)
    user_categories: dict[UUID, int] = field(default_factory=dict)
    shift_users: dict[UUID, UUID] = field(default_factory=dict)
    details: dict[UUID, ShiftReportDetail] = field(default_factory=dict)
    created_details: list[CreateShiftReportDetailPayload] = field(default_factory=list)
    updated_details: list[UpdateShiftReportDetailCommand] = field(default_factory=list)
    created_reports: list[CreateShiftReportCommand] = field(default_factory=list)

    # availability port
    def get_shift_report_performer_category(self, shift_report_id):
        user = self.shift_users.get(shift_report_id)
        return None if user is None else self.user_categories[user]

    def get_user_categories(self, user_ids):
        return {u: self.user_categories[u] for u in user_ids if u in self.user_categories}

    def get_unavailable_work_ids(self, work_ids, category):
        return {w for w in work_ids if self.prices.get((w, category)) == Decimal("-1")}

    # writes
    def create_shift_report_detail(self, command):
        self.created_details.append(command)
        return _detail(command.shift_report, command.work)

    def get_shift_report_detail(self, shift_report_detail_id):
        return self.details.get(shift_report_detail_id)

    def update_shift_report_detail(self, command):
        self.updated_details.append(command)
        current = self.details.get(command.shift_report_detail_id)
        if current is None:
            return None
        return current.with_updates(work=command.work or current.work)

    def create_shift_report(self, command):
        self.created_reports.append(command)
        return object()

    def create_shift_reports(self, commands):
        self.created_reports.extend(commands)
        return [object() for _ in commands]


def _detail(shift_report: UUID, work: UUID) -> ShiftReportDetail:
    return ShiftReportDetail(
        shift_report_detail_id=uuid4(),
        shift_report=shift_report,
        project_work=None,
        work=work,
        quantity=Decimal("1"),
        summ=Decimal("10"),
        created_by=uuid4(),
        created_at=1,
    )


@pytest.fixture
def world():
    """Performer has category 1; the requester (admin) has category 0."""
    performer, requester = uuid4(), uuid4()
    shift = uuid4()
    blocked, free, paid = uuid4(), uuid4(), uuid4()
    repo = _Repository(
        prices={
            (blocked, 1): Decimal("-1"),
            (blocked, 0): Decimal("100"),  # allowed for the requester's category
            (free, 1): Decimal("0"),
            (paid, 1): Decimal("50"),
        },
        user_categories={performer: 1, requester: 0},
        shift_users={shift: performer},
    )
    return {
        "repo": repo,
        "performer": performer,
        "requester": requester,
        "shift": shift,
        "blocked": blocked,
        "free": free,
        "paid": paid,
    }


def _payload(world, work):
    return CreateShiftReportDetailPayload(
        shift_report=world["shift"],
        project_work=None,
        work=work,
        quantity=Decimal("1"),
        created_by=world["requester"],
    )


def test_add_rejects_work_priced_minus_one_for_performer_category(world):
    with pytest.raises(ShiftReportWorkUnavailableError) as raised:
        CreateShiftReportDetailUseCase(world["repo"]).execute(
            _payload(world, world["blocked"])
        )
    assert str(raised.value) == MESSAGE
    assert raised.value.work_ids == (world["blocked"],)
    assert world["repo"].created_details == []


@pytest.mark.parametrize("key", ["free", "paid"])
def test_add_allows_zero_and_positive_price(world, key):
    CreateShiftReportDetailUseCase(world["repo"]).execute(_payload(world, world[key]))
    assert len(world["repo"].created_details) == 1


def test_check_uses_performer_category_not_requester(world):
    """The requester's own category (0) allows the work; the performer's does not."""
    repo = world["repo"]
    assert repo.get_unavailable_work_ids({world["blocked"]}, 0) == set()
    with pytest.raises(ShiftReportWorkUnavailableError):
        CreateShiftReportDetailUseCase(repo).execute(_payload(world, world["blocked"]))


def test_bulk_add_rejects_whole_batch_before_any_write(world):
    commands = [
        _payload(world, world["paid"]),
        _payload(world, world["free"]),
        _payload(world, world["blocked"]),
    ]
    with pytest.raises(ShiftReportWorkUnavailableError) as raised:
        CreateShiftReportDetailUseCase(world["repo"]).execute_many(commands)
    assert raised.value.work_ids == (world["blocked"],)
    assert world["repo"].created_details == []


def test_bulk_add_writes_all_when_every_work_available(world):
    commands = [_payload(world, world["paid"]), _payload(world, world["free"])]
    result = CreateShiftReportDetailUseCase(world["repo"]).execute_many(commands)
    assert len(result) == 2
    assert world["repo"].created_details == commands


def test_replace_with_unavailable_work_is_rejected(world):
    detail = _detail(world["shift"], world["paid"])
    world["repo"].details[detail.shift_report_detail_id] = detail
    with pytest.raises(ShiftReportWorkUnavailableError):
        UpdateShiftReportDetailUseCase(world["repo"]).execute(
            UpdateShiftReportDetailCommand(
                shift_report_detail_id=detail.shift_report_detail_id,
                work=world["blocked"],
            )
        )
    assert world["repo"].updated_details == []


def test_replace_with_zero_priced_work_is_allowed(world):
    detail = _detail(world["shift"], world["paid"])
    world["repo"].details[detail.shift_report_detail_id] = detail
    updated = UpdateShiftReportDetailUseCase(world["repo"]).execute(
        UpdateShiftReportDetailCommand(
            shift_report_detail_id=detail.shift_report_detail_id, work=world["free"]
        )
    )
    assert updated.work == world["free"]


@pytest.mark.parametrize(
    "changes",
    [
        {"work": "same"},
        {"quantity": Decimal("1")},
        {"project_work": "new"},
        {"shift_report": "same"},
    ],
    ids=["same-work-resent", "same-quantity-resent", "project-work-only", "same-shift"],
)
def test_historical_unavailable_detail_stays_editable(world, changes):
    """Edits that change neither work, shift nor quantity are not re-checked."""
    detail = _detail(world["shift"], world["blocked"])
    world["repo"].details[detail.shift_report_detail_id] = detail
    resolved = {
        "work": world["blocked"],
        "project_work": uuid4(),
        "shift_report": world["shift"],
    }
    changes = {
        key: resolved[key] if isinstance(value, str) else value
        for key, value in changes.items()
    }
    UpdateShiftReportDetailUseCase(world["repo"]).execute(
        UpdateShiftReportDetailCommand(
            shift_report_detail_id=detail.shift_report_detail_id, **changes
        )
    )
    assert len(world["repo"].updated_details) == 1


def test_quantity_change_of_unavailable_detail_is_rejected(world):
    """`-1` cannot price a new quantity, so the saved accrual would not match it."""
    detail = _detail(world["shift"], world["blocked"])
    world["repo"].details[detail.shift_report_detail_id] = detail
    with pytest.raises(ShiftReportWorkUnavailableError) as raised:
        UpdateShiftReportDetailUseCase(world["repo"]).execute(
            UpdateShiftReportDetailCommand(
                shift_report_detail_id=detail.shift_report_detail_id,
                quantity=Decimal("3"),
            )
        )
    assert raised.value.work_ids == (world["blocked"],)
    assert world["repo"].updated_details == []


@pytest.mark.parametrize("key", ["free", "paid"])
def test_quantity_change_of_available_detail_is_allowed(world, key):
    detail = _detail(world["shift"], world[key])
    world["repo"].details[detail.shift_report_detail_id] = detail
    UpdateShiftReportDetailUseCase(world["repo"]).execute(
        UpdateShiftReportDetailCommand(
            shift_report_detail_id=detail.shift_report_detail_id,
            quantity=Decimal("3"),
        )
    )
    assert len(world["repo"].updated_details) == 1


@pytest.fixture
def other_shift(world):
    """A shift whose performer has category 2, where `paid` is unavailable."""
    repo = world["repo"]
    performer, shift = uuid4(), uuid4()
    repo.user_categories[performer] = 2
    repo.shift_users[shift] = performer
    repo.prices[(world["paid"], 2)] = Decimal("-1")
    repo.prices[(world["free"], 2)] = Decimal("0")
    return shift


def test_move_without_work_checks_current_work_for_target_performer(
    world, other_shift
):
    detail = _detail(world["shift"], world["paid"])
    world["repo"].details[detail.shift_report_detail_id] = detail
    with pytest.raises(ShiftReportWorkUnavailableError) as raised:
        UpdateShiftReportDetailUseCase(world["repo"]).execute(
            UpdateShiftReportDetailCommand(
                shift_report_detail_id=detail.shift_report_detail_id,
                shift_report=other_shift,
            )
        )
    assert raised.value.work_ids == (world["paid"],)
    assert world["repo"].updated_details == []


def test_move_with_same_work_is_checked(world, other_shift):
    detail = _detail(world["shift"], world["paid"])
    world["repo"].details[detail.shift_report_detail_id] = detail
    with pytest.raises(ShiftReportWorkUnavailableError):
        UpdateShiftReportDetailUseCase(world["repo"]).execute(
            UpdateShiftReportDetailCommand(
                shift_report_detail_id=detail.shift_report_detail_id,
                shift_report=other_shift,
                work=world["paid"],
            )
        )
    assert world["repo"].updated_details == []


def test_move_with_new_work_uses_target_performer_category(world, other_shift):
    """`blocked` is fine for category 2 but not for the source performer (1)."""
    detail = _detail(world["shift"], world["free"])
    world["repo"].details[detail.shift_report_detail_id] = detail
    UpdateShiftReportDetailUseCase(world["repo"]).execute(
        UpdateShiftReportDetailCommand(
            shift_report_detail_id=detail.shift_report_detail_id,
            shift_report=other_shift,
            work=world["blocked"],
        )
    )
    assert len(world["repo"].updated_details) == 1


def test_move_allowed_when_work_available_for_target_performer(world, other_shift):
    detail = _detail(world["shift"], world["free"])
    world["repo"].details[detail.shift_report_detail_id] = detail
    UpdateShiftReportDetailUseCase(world["repo"]).execute(
        UpdateShiftReportDetailCommand(
            shift_report_detail_id=detail.shift_report_detail_id,
            shift_report=other_shift,
        )
    )
    assert len(world["repo"].updated_details) == 1


def test_move_to_unknown_shift_is_not_found(world):
    detail = _detail(world["shift"], world["paid"])
    world["repo"].details[detail.shift_report_detail_id] = detail
    with pytest.raises(ShiftReportNotFoundError):
        UpdateShiftReportDetailUseCase(world["repo"]).execute(
            UpdateShiftReportDetailCommand(
                shift_report_detail_id=detail.shift_report_detail_id,
                shift_report=uuid4(),
            )
        )
    assert world["repo"].updated_details == []


def test_replace_unknown_detail_is_not_found(world):
    with pytest.raises(ShiftReportNotFoundError):
        UpdateShiftReportDetailUseCase(world["repo"]).execute(
            UpdateShiftReportDetailCommand(
                shift_report_detail_id=uuid4(), work=world["paid"]
            )
        )


def _shift_command(world, user, work):
    return CreateShiftReportCommand(
        user=user,
        date=1,
        project=uuid4(),
        details=[CreateShiftReportDetailCommand(project_work=None, work=work, quantity=Decimal("1"))],
    )


def test_create_shift_with_unavailable_detail_is_rejected(world):
    with pytest.raises(ShiftReportWorkUnavailableError):
        CreateShiftReportUseCase(world["repo"]).execute(
            _shift_command(world, world["performer"], world["blocked"]),
            ShiftReportActor(role="admin", user_id=world["requester"]),
        )
    assert world["repo"].created_reports == []


def test_create_shift_for_other_performer_category_is_allowed(world):
    """Same work, performer of category 0: the price there is 100."""
    CreateShiftReportUseCase(world["repo"]).execute(
        _shift_command(world, world["requester"], world["blocked"]),
        ShiftReportActor(role="admin", user_id=world["requester"]),
    )
    assert len(world["repo"].created_reports) == 1


def test_bulk_create_shifts_rejects_all_if_one_performer_cannot_do_work(world):
    commands = [
        _shift_command(world, world["requester"], world["blocked"]),
        _shift_command(world, world["performer"], world["blocked"]),
    ]
    with pytest.raises(ShiftReportWorkUnavailableError):
        CreateShiftReportsUseCase(world["repo"]).execute(
            commands, ShiftReportActor(role="admin", user_id=world["requester"])
        )
    assert world["repo"].created_reports == []


def test_availability_use_case_reports_flags_and_reason(world):
    result = GetShiftWorkAvailabilityUseCase(world["repo"]).execute(
        world["shift"], [world["blocked"], world["free"], world["paid"]]
    )
    assert result[world["blocked"]].available is False
    assert result[world["blocked"]].reason == MESSAGE
    assert result[world["free"]].available is True
    assert result[world["free"]].reason is None
    assert result[world["paid"]].available is True


def test_availability_use_case_unknown_shift_is_not_found(world):
    with pytest.raises(ShiftReportNotFoundError):
        GetShiftWorkAvailabilityUseCase(world["repo"]).execute(uuid4(), [world["paid"]])
