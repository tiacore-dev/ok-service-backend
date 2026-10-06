from app.database.models import SystemSettings


def _seed_system_prompt(db_session, value=None, name="Системный промпт"):
    setting = SystemSettings(
        system_setting_id="system_prompt", name=name, value=value
    )
    db_session.add(setting)
    db_session.commit()
    return setting


def test_system_settings_can_be_listed_and_viewed(client, jwt_token, db_session):
    _seed_system_prompt(db_session)
    headers = {"Authorization": f"Bearer {jwt_token}"}

    response = client.get("/system_settings/all", headers=headers)
    assert response.status_code == 200
    assert response.json["system_settings"] == [
        {
            "system_setting_id": "system_prompt",
            "name": "Системный промпт",
            "value": None,
            "modified_at": None,
            "modified_by": None,
        }
    ]

    response = client.get("/system_settings/system_prompt/view", headers=headers)
    assert response.status_code == 200
    assert response.json["system_setting"] == {
        "system_setting_id": "system_prompt",
        "name": "Системный промпт",
        "value": None,
        "modified_at": None,
        "modified_by": None,
    }


def test_admin_can_edit_system_setting_value_including_null(
    client, jwt_token_admin, seed_admin, db_session
):
    _seed_system_prompt(db_session, "Initial prompt")
    headers = {"Authorization": f"Bearer {jwt_token_admin}"}

    response = client.patch(
        "/system_settings/system_prompt/edit",
        json={"value": "Updated prompt"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json["system_setting"]["value"] == "Updated prompt"
    assert response.json["system_setting"]["modified_by"] == seed_admin["user_id"]

    response = client.patch(
        "/system_settings/system_prompt/edit", json={"value": None}, headers=headers
    )
    assert response.status_code == 200
    assert response.json["system_setting"]["value"] is None

    response = client.patch(
        "/system_settings/system_prompt/edit",
        json={"name": "Обновлённый системный промпт"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json["system_setting"]["name"] == "Обновлённый системный промпт"


def test_non_admin_cannot_edit_system_setting(client, jwt_token_user, db_session):
    _seed_system_prompt(db_session, "Initial prompt")
    response = client.patch(
        "/system_settings/system_prompt/edit",
        json={"value": "Changed"},
        headers={"Authorization": f"Bearer {jwt_token_user}"},
    )
    assert response.status_code == 403


def test_system_setting_edit_validates_value_and_missing_setting(
    client, jwt_token_admin, db_session
):
    _seed_system_prompt(db_session)
    headers = {"Authorization": f"Bearer {jwt_token_admin}"}

    response = client.patch(
        "/system_settings/system_prompt/edit", json={}, headers=headers
    )
    assert response.status_code == 400

    response = client.patch(
        "/system_settings/system_prompt/edit", json={"name": None}, headers=headers
    )
    assert response.status_code == 400

    response = client.get(
        "/system_settings/unknown/view", headers=headers
    )
    assert response.status_code == 404


def test_system_settings_do_not_expose_create_or_delete_routes(
    client, jwt_token_admin
):
    headers = {"Authorization": f"Bearer {jwt_token_admin}"}
    assert client.post("/system_settings/add", json={}, headers=headers).status_code == 404
    assert client.delete(
        "/system_settings/system_prompt/delete/hard", headers=headers
    ).status_code == 404
