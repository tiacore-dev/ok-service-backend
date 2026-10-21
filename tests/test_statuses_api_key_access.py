from uuid import uuid4

import pytest

from app.database.models import ApiKeys, KeyPermissionTypeRelations, PermissionTypes
from app.database.time_utils import utc_epoch_milliseconds
from app.utils.api_key_permissions import set_api_key_permissions


STATUS_ROUTES = [
    (
        "/projects/statuses",
        "projects-statuses",
        [
            {"value": "pending", "label": "На согласовании"},
            {"value": "in_progress", "label": "В работе"},
            {"value": "works_completed", "label": "Работы выполнены"},
            {"value": "closed", "label": "Закрыто"},
        ],
    ),
    (
        "/objects/statuses",
        "objects-statuses",
        [
            {"value": "waiting", "label": "В Ожидании"},
            {"value": "active", "label": "Действующий"},
            {"value": "completed", "label": "Завершенный"},
        ],
    ),
]


def test_status_permissions_are_listed_for_api_keys(client, jwt_token_admin):
    # Shared cleanup removes permission types between tests.
    set_api_key_permissions()
    response = client.get(
        "/api-key/permission-types/all",
        headers={"Authorization": f"Bearer {jwt_token_admin}"},
    )
    assert response.status_code == 200
    permissions = {
        (item["code"], item["description"])
        for item in response.get_json()["permission_types"]
    }
    for route, code, _ in STATUS_ROUTES:
        assert (code, f"GET {route}") in permissions


@pytest.mark.parametrize("route,code,statuses", STATUS_ROUTES)
@pytest.mark.parametrize(
    "key_state", ["granted", "missing_permission", "wrong_permission", "invalid", "expired"]
)
def test_status_route_requires_its_own_api_key_permission(
    client, db_session, route, code, statuses, key_state
):
    set_api_key_permissions()
    key = ApiKeys(
        api_key_id=uuid4(),
        name=f"statuses-{uuid4()}",
        token=str(uuid4()),
        expires_at=utc_epoch_milliseconds() - 1 if key_state == "expired" else None,
    )
    db_session.add(key)
    if key_state != "missing_permission":
        permission_code = code
        if key_state == "wrong_permission":
            permission_code = (
                "objects-statuses" if code == "projects-statuses" else "projects-statuses"
            )
        permission = db_session.query(PermissionTypes).filter_by(code=permission_code).one()
        db_session.add(
            KeyPermissionTypeRelations(
                api_key_id=key.api_key_id,
                permission_type_id=permission.permission_type_id,
            )
        )
    db_session.commit()

    response = client.get(
        route, headers={"API-Key": "invalid" if key_state == "invalid" else key.token}
    )
    assert response.status_code == (200 if key_state == "granted" else 403)
    if key_state == "granted":
        assert response.get_json()["statuses"] == statuses


@pytest.mark.parametrize("route,code,statuses", STATUS_ROUTES)
def test_status_route_preserves_jwt_access(client, jwt_token_user, route, code, statuses):
    response = client.get(route, headers={"Authorization": f"Bearer {jwt_token_user}"})
    assert response.status_code == 200
    assert response.get_json()["statuses"] == statuses
