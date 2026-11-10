"""API + PostgreSQL: works priced `-1` for the shift performer category.

The performer (`seed_user`, role `user`) gets category 1. The requesting admin
keeps a different category, so every check proves the rule follows the shift
performer and not the requester.
"""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

MESSAGE = "Работа недоступна для категории исполнителя"
CODE = "WORK_UNAVAILABLE_FOR_PERFORMER_CATEGORY"
PERFORMER_CATEGORY = 1


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def performer(db_session, seed_user):
    from app.database.models import Users

    user = db_session.get(Users, UUID(seed_user["user_id"]))
    user.category = PERFORMER_CATEGORY
    db_session.commit()
    return seed_user


@pytest.fixture
def add_work(db_session, seed_work_category, seed_measurement_units, seed_user):
    from app.database.models import Works

    def _add(name):
        work = Works(
            work_id=uuid4(),
            name=name,
            category=UUID(seed_work_category["work_category_id"]),
            measurement_unit=UUID(seed_measurement_units["м"]["measurement_unit_id"]),
            created_by=UUID(seed_user["user_id"]),
            deleted=False,
        )
        db_session.add(work)
        db_session.commit()
        return work.work_id

    return _add


@pytest.fixture
def set_price(db_session, seed_user):
    from app.database.models import WorkPrices

    def _set(work_id, category, price):
        db_session.add(
            WorkPrices(
                work_price_id=uuid4(),
                work=work_id,
                category=category,
                price=Decimal(str(price)),
                created_by=UUID(seed_user["user_id"]),
                deleted=False,
            )
        )
        db_session.commit()

    return _set


@pytest.fixture
def works(add_work, set_price, performer):
    """blocked: -1 for the performer; free: 0; paid: 40."""
    blocked, free, paid = add_work("Blocked"), add_work("Free"), add_work("Paid")
    set_price(blocked, PERFORMER_CATEGORY, -1)
    set_price(blocked, 0, 100)  # the admin requester's category allows it
    set_price(free, PERFORMER_CATEGORY, 0)
    set_price(paid, PERFORMER_CATEGORY, 40)
    return {"blocked": blocked, "free": free, "paid": paid}


@pytest.fixture
def project_work(db_session, seed_project, seed_user, works):
    from app.database.models import ProjectWorks

    rows = {}
    for key, work_id in works.items():
        row = ProjectWorks(
            project_work_id=uuid4(),
            project_work_name=key,
            project=UUID(seed_project["project_id"]),
            work=work_id,
            quantity=100,
            created_by=UUID(seed_user["user_id"]),
        )
        db_session.add(row)
        rows[key] = row.project_work_id
    db_session.commit()
    return rows


@pytest.fixture
def shift(seed_shift_report, performer):
    return seed_shift_report["shift_report_id"]


@pytest.fixture
def historical_detail(db_session, shift, works, project_work, seed_user):
    """Saved before the price became -1; its accrual must never change."""
    from app.database.models import ShiftReportDetails

    detail = ShiftReportDetails(
        shift_report_detail_id=uuid4(),
        shift_report=UUID(shift),
        project_work=project_work["blocked"],
        work=works["blocked"],
        quantity=Decimal("2"),
        summ=Decimal("105.00"),
        created_by=UUID(seed_user["user_id"]),
    )
    db_session.add(detail)
    db_session.commit()
    return detail.shift_report_detail_id


def _detail(shift, works, project_work, key, quantity=2):
    return {
        "shift_report": shift,
        "project_work": str(project_work[key]),
        "work": str(works[key]),
        "quantity": quantity,
    }


def _assert_unavailable(response, *work_ids):
    assert response.status_code == 409, response.json
    assert response.json == {
        "msg": MESSAGE,
        "code": CODE,
        "work_ids": sorted(str(work_id) for work_id in work_ids),
    }


def _detail_count(db_session):
    from app.database.models import ShiftReportDetails

    db_session.expire_all()
    return db_session.query(ShiftReportDetails).count()


# --- adding -----------------------------------------------------------------


@pytest.mark.parametrize("token", ["jwt_token", "jwt_token_user"], ids=["admin", "performer"])
def test_add_unavailable_work_rejected_for_any_requester(
    request, client, db_session, shift, works, project_work, token
):
    response = client.post(
        "/shift_report_details/add",
        json=_detail(shift, works, project_work, "blocked"),
        headers=_auth(request.getfixturevalue(token)),
    )
    _assert_unavailable(response, works["blocked"])
    assert _detail_count(db_session) == 0


@pytest.mark.parametrize("key,expected", [("free", Decimal("0")), ("paid", Decimal("80"))])
def test_add_zero_and_positive_priced_work(
    client, db_session, jwt_token, shift, works, project_work, key, expected
):
    from app.database.models import ShiftReportDetails

    response = client.post(
        "/shift_report_details/add",
        json=_detail(shift, works, project_work, key),
        headers=_auth(jwt_token),
    )
    assert response.status_code == 200, response.json
    detail = db_session.get(
        ShiftReportDetails, UUID(response.json["shift_report_detail_id"])
    )
    assert detail.summ == expected


def test_requester_category_restriction_does_not_block_performer(
    client, db_session, jwt_token, seed_admin, shift, works, project_work, set_price
):
    """-1 for the requester's category is irrelevant; the performer's is 0."""
    from app.database.models import Users

    admin = db_session.get(Users, UUID(seed_admin["user_id"]))
    admin.category = 3
    db_session.commit()
    set_price(works["free"], 3, -1)

    response = client.post(
        "/shift_report_details/add",
        json=_detail(shift, works, project_work, "free"),
        headers=_auth(jwt_token),
    )
    assert response.status_code == 200, response.json


def test_add_many_is_rejected_atomically(
    client, db_session, jwt_token, shift, works, project_work
):
    response = client.post(
        "/shift_report_details/add/many",
        json=[
            _detail(shift, works, project_work, "paid"),
            _detail(shift, works, project_work, "free"),
            _detail(shift, works, project_work, "blocked"),
        ],
        headers=_auth(jwt_token),
    )
    _assert_unavailable(response, works["blocked"])
    assert _detail_count(db_session) == 0


def test_add_many_succeeds_when_all_available(
    client, db_session, jwt_token, shift, works, project_work
):
    response = client.post(
        "/shift_report_details/add/many",
        json=[
            _detail(shift, works, project_work, "paid"),
            _detail(shift, works, project_work, "free"),
        ],
        headers=_auth(jwt_token),
    )
    assert response.status_code == 200, response.json
    assert len(response.json["shift_report_detail_ids"]) == 2
    assert _detail_count(db_session) == 2


def test_create_shift_with_unavailable_detail_creates_nothing(
    client, db_session, jwt_token, performer, seed_project, works, project_work
):
    from app.database.models import ShiftReports

    response = client.post(
        "/shift_reports/add",
        json={
            "user": performer["user_id"],
            "date": 20240105,
            "project": seed_project["project_id"],
            "details": [
                {"work": str(works["paid"]), "quantity": 1,
                 "project_work": str(project_work["paid"])},
                {"work": str(works["blocked"]), "quantity": 1,
                 "project_work": str(project_work["blocked"])},
            ],
        },
        headers=_auth(jwt_token),
    )
    _assert_unavailable(response, works["blocked"])
    db_session.expire_all()
    assert db_session.query(ShiftReports).count() == 0
    assert _detail_count(db_session) == 0


def test_bulk_create_shifts_rejected_if_any_performer_cannot_do_work(
    client, db_session, jwt_token_admin, performer, seed_leader, seed_project,
    works, project_work,
):
    from app.database.models import ShiftReports

    response = client.post(
        "/shift_reports/add-bulk",
        json={
            # the leader has category 0 (price 100); the performer has -1
            "user_ids": [seed_leader["user_id"], performer["user_id"]],
            "date": 20240106,
            "project": seed_project["project_id"],
            "details": [
                {"work": str(works["blocked"]), "quantity": 1,
                 "project_work": str(project_work["blocked"])},
            ],
        },
        headers=_auth(jwt_token_admin),
    )
    _assert_unavailable(response, works["blocked"])
    db_session.expire_all()
    assert db_session.query(ShiftReports).count() == 0


# --- replacing and historical records ---------------------------------------


def test_replace_with_unavailable_work_rejected_and_detail_unchanged(
    client, db_session, jwt_token_user, shift, works, project_work, seed_user
):
    from app.database.models import ShiftReportDetails

    created = client.post(
        "/shift_report_details/add",
        json=_detail(shift, works, project_work, "paid"),
        headers=_auth(jwt_token_user),
    )
    detail_id = UUID(created.json["shift_report_detail_id"])

    response = client.patch(
        f"/shift_report_details/{detail_id}/edit",
        json={"work": str(works["blocked"]), "quantity": 9},
        headers=_auth(jwt_token_user),
    )
    _assert_unavailable(response, works["blocked"])
    db_session.expire_all()
    detail = db_session.get(ShiftReportDetails, detail_id)
    assert detail.work == works["paid"]
    assert detail.quantity == Decimal("2")
    assert detail.summ == Decimal("80")


def test_historical_detail_is_readable(
    client, jwt_token, historical_detail, shift
):
    view = client.get(
        f"/shift_report_details/{historical_detail}/view", headers=_auth(jwt_token)
    )
    assert view.status_code == 200
    assert view.json["shift_report_detail"]["summ"] == 105.0
    listed = client.get(
        f"/shift_report_details/all?shift_report={shift}", headers=_auth(jwt_token)
    )
    assert listed.status_code == 200
    assert [d["shift_report_detail_id"] for d in listed.json["shift_report_details"]] == [
        str(historical_detail)
    ]


def test_historical_detail_quantity_change_rejected_and_accrual_kept(
    client, db_session, jwt_token, historical_detail, works
):
    """-1 cannot price a new quantity, so the change is rejected as a whole."""
    from app.database.models import ShiftReportDetails

    response = client.patch(
        f"/shift_report_details/{historical_detail}/edit",
        json={"quantity": 5},
        headers=_auth(jwt_token),
    )
    _assert_unavailable(response, works["blocked"])
    db_session.expire_all()
    detail = db_session.get(ShiftReportDetails, historical_detail)
    assert detail.quantity == Decimal("2")
    assert detail.summ == Decimal("105.00")


def test_historical_detail_same_quantity_edit_allowed(
    client, db_session, jwt_token, historical_detail
):
    from app.database.models import ShiftReportDetails

    response = client.patch(
        f"/shift_report_details/{historical_detail}/edit",
        json={"quantity": 2},
        headers=_auth(jwt_token),
    )
    assert response.status_code == 200, response.json
    db_session.expire_all()
    assert db_session.get(ShiftReportDetails, historical_detail).summ == Decimal(
        "105.00"
    )


def test_manager_rejects_quantity_change_for_unavailable_price(
    db_session, historical_detail
):
    """Database-layer guard: the record is rolled back, not left inconsistent."""
    from app.database.managers.shift_reports_managers import ShiftReportsDetailsManager
    from app.database.models import ShiftReportDetails
    from app.domain.shift_reports import ShiftReportWorkUnavailableError

    with pytest.raises(ShiftReportWorkUnavailableError):
        ShiftReportsDetailsManager().update_shift_report_details(
            historical_detail, quantity=Decimal("7")
        )
    db_session.expire_all()
    detail = db_session.get(ShiftReportDetails, historical_detail)
    assert detail.quantity == Decimal("2")
    assert detail.summ == Decimal("105.00")


def test_condition_recalculation_keeps_historical_accrual(
    db_session, historical_detail, shift, performer
):
    from app.database.managers.shift_reports_managers import ShiftReportsDetailsManager
    from app.database.models import ShiftReportDetails

    ShiftReportsDetailsManager().recalculate_by_conditions(
        shift, extreme_conditions=True, night_shift=True, user=performer["user_id"]
    )
    db_session.expire_all()
    assert db_session.get(ShiftReportDetails, historical_detail).summ == Decimal("105.00")


# --- work selection API -----------------------------------------------------


def _flags(items, id_key="work"):
    return {
        str(item[id_key]): (item["available"], item["unavailable_reason"])
        for item in items
    }


def test_works_list_reports_availability_for_shift(client, jwt_token_user, shift, works):
    response = client.get(
        f"/works/all?shift_report={shift}&limit=100", headers=_auth(jwt_token_user)
    )
    assert response.status_code == 200, response.json
    flags = _flags(response.json["works"], "work_id")
    assert flags[str(works["blocked"])] == (False, MESSAGE)
    assert flags[str(works["free"])] == (True, None)
    assert flags[str(works["paid"])] == (True, None)


def test_works_list_without_shift_has_no_availability(client, jwt_token, works):
    response = client.get("/works/all?limit=100", headers=_auth(jwt_token))
    assert response.status_code == 200
    assert all(item["available"] is None for item in response.json["works"])


def test_works_list_unknown_shift_is_404(client, jwt_token, works):
    response = client.get(f"/works/all?shift_report={uuid4()}", headers=_auth(jwt_token))
    assert response.status_code == 404


def test_project_works_list_reports_availability_for_shift(
    client, jwt_token, shift, works, project_work, seed_project
):
    response = client.get(
        f"/project_works/all?project={seed_project['project_id']}&shift_report={shift}",
        headers=_auth(jwt_token),
    )
    assert response.status_code == 200, response.json
    flags = _flags(response.json["project_works"])
    assert flags[str(works["blocked"])] == (False, MESSAGE)
    assert flags[str(works["free"])] == (True, None)
    assert flags[str(works["paid"])] == (True, None)


def test_project_works_list_without_shift_is_unchanged(
    client, jwt_token, project_work, seed_project
):
    response = client.get(
        f"/project_works/all?project={seed_project['project_id']}",
        headers=_auth(jwt_token),
    )
    assert response.status_code == 200
    for item in response.json["project_works"]:
        assert "available" not in item
        assert "unavailable_reason" not in item


# --- work_prices API and DB constraint --------------------------------------


@pytest.mark.parametrize("price", [-1, 0, 12.5])
def test_work_price_api_accepts_allowed_values(client, db_session, jwt_token, seed_work, price):
    from app.database.models import WorkPrices

    response = client.post(
        "/work_prices/add",
        json={"work": seed_work["work_id"], "category": 2, "price": price},
        headers=_auth(jwt_token),
    )
    assert response.status_code == 200, response.json
    view = client.get(
        f"/work_prices/{response.json['work_price_id']}/view", headers=_auth(jwt_token)
    )
    assert view.status_code == 200
    assert view.json["work_price"]["price"] == price
    stored = db_session.get(WorkPrices, UUID(response.json["work_price_id"]))
    assert stored.price == Decimal(str(price))


@pytest.mark.parametrize("price", [-2, -1.5, -0.5])
def test_work_price_api_rejects_values_below_minus_one(
    client, db_session, jwt_token, seed_work, price
):
    from app.database.models import WorkPrices

    response = client.post(
        "/work_prices/add",
        json={"work": seed_work["work_id"], "category": 2, "price": price},
        headers=_auth(jwt_token),
    )
    assert response.status_code == 400
    assert db_session.query(WorkPrices).count() == 0


def test_work_price_edit_to_minus_one_and_rejects_below(
    client, db_session, jwt_token, seed_work_price
):
    from app.database.models import WorkPrices

    url = f"/work_prices/{seed_work_price['work_price_id']}/edit"
    assert client.patch(url, json={"price": -1}, headers=_auth(jwt_token)).status_code == 200
    assert client.patch(url, json={"price": -3}, headers=_auth(jwt_token)).status_code == 400
    db_session.expire_all()
    stored = db_session.get(WorkPrices, UUID(seed_work_price["work_price_id"]))
    assert stored.price == Decimal("-1")


@pytest.mark.parametrize("price,ok", [(-1, True), (0, True), (5, True), (-2, False), (-0.5, False)])
def test_database_constraint(db_session, seed_work, seed_user, price, ok):
    from app.database.models import WorkPrices

    db_session.add(
        WorkPrices(
            work_price_id=uuid4(),
            work=UUID(seed_work["work_id"]),
            category=1,
            price=Decimal(str(price)),
            created_by=UUID(seed_user["user_id"]),
            deleted=False,
        )
    )
    if ok:
        db_session.commit()
    else:
        with pytest.raises(IntegrityError, match="check_work_prices_price_values"):
            db_session.commit()
        db_session.rollback()
