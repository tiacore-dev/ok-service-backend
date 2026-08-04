from uuid import uuid4

from app.database.models import ApiKeys, PermissionTypes


def _auth_headers(jwt_token_admin):
    return {"Authorization": f"Bearer {jwt_token_admin}"}


def _create_api_key(client, headers, api_key_name):
    response = client.post(
        "/api-key/generate",
        headers=headers,
        json={"name": api_key_name, "expires_at": 1_893_456_000_000},
    )
    assert response.status_code == 200
    return response.get_json()


def test_api_key_generate_endpoint_creates_api_key_and_public_views(
    client, jwt_token_admin, db_session
):
    headers = _auth_headers(jwt_token_admin)
    api_key_name = f"api-key-{uuid4().hex[:12]}"
    expires_at = 1_893_456_000_000

    response = client.post(
        "/api-key/generate",
        headers=headers,
        json={"name": api_key_name, "expires_at": expires_at},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["msg"] == "API key generated successfully"
    assert isinstance(body["api_key_id"], str)
    assert isinstance(body["token"], str)

    stored = db_session.query(ApiKeys).filter_by(name=api_key_name).one()
    stored_api_key_id = str(stored.api_key_id)
    stored_token = stored.token
    stored_public = stored.to_public_dict()
    assert stored_api_key_id == body["api_key_id"]
    assert stored_token == body["token"]

    all_response = client.get("/api-key/all", headers=headers)
    assert all_response.status_code == 200
    api_keys = all_response.get_json()["api_keys"]
    assert any(
        item["api_key_id"] == body["api_key_id"]
        and item["name"] == api_key_name
        and item["expires_at"] == expires_at
        for item in api_keys
    )
    assert all("token" not in item for item in api_keys)

    view_response = client.get(f"/api-key/{body['api_key_id']}/view", headers=headers)
    assert view_response.status_code == 200
    assert view_response.get_json()["api_key"] == stored_public

    delete_response = client.delete(
        f"/api-key/{body['api_key_id']}/delete", headers=headers
    )
    assert delete_response.status_code == 200
    assert delete_response.get_json() == {
        "msg": "API key deleted successfully",
        "api_key_id": body["api_key_id"],
    }

    assert (
        client.get(f"/api-key/{body['api_key_id']}/view", headers=headers).status_code
        == 404
    )


def test_api_key_generate_endpoint_rejects_duplicate_name(
    client, jwt_token_admin, db_session
):
    headers = _auth_headers(jwt_token_admin)
    api_key_name = f"api-key-{uuid4().hex[:12]}"

    first_response = client.post(
        "/api-key/generate",
        headers=headers,
        json={"name": api_key_name, "expires_at": 1_893_456_000_000},
    )
    assert first_response.status_code == 200

    duplicate_response = client.post(
        "/api-key/generate",
        headers=headers,
        json={"name": api_key_name, "expires_at": 1_893_456_000_001},
    )
    assert duplicate_response.status_code == 409
    assert duplicate_response.get_json()["msg"] == "API key with this name already exists"


def test_api_key_permission_relation_endpoints_work(client, jwt_token_admin, db_session):
    headers = _auth_headers(jwt_token_admin)
    api_key_name = f"api-key-{uuid4().hex[:12]}"

    api_key_id = _create_api_key(client, headers, api_key_name)["api_key_id"]

    permission_type_one = PermissionTypes(
        permission_type_id=uuid4(),
        code=f"api-key-test-{uuid4().hex[:8]}",
        description="First permission type",
    )
    permission_type_two = PermissionTypes(
        permission_type_id=uuid4(),
        code=f"api-key-test-{uuid4().hex[:8]}",
        description="Second permission type",
    )
    permission_type_three = PermissionTypes(
        permission_type_id=uuid4(),
        code=f"api-key-test-{uuid4().hex[:8]}",
        description="Third permission type",
    )
    db_session.add_all(
        [permission_type_one, permission_type_two, permission_type_three]
    )
    permission_type_one_id = str(permission_type_one.permission_type_id)
    permission_type_two_id = str(permission_type_two.permission_type_id)
    permission_type_three_id = str(permission_type_three.permission_type_id)
    db_session.commit()

    permission_types_response = client.get(
        "/api-key/permission-types/all", headers=headers
    )
    assert permission_types_response.status_code == 200
    permission_types = permission_types_response.get_json()["permission_types"]
    assert any(
        item["permission_type_id"] == permission_type_one_id
        for item in permission_types
    )
    assert any(
        item["permission_type_id"] == permission_type_two_id
        for item in permission_types
    )

    relation_response = client.post(
        "/api-key/permissions/add",
        headers=headers,
        json={
            "api_key_id": api_key_id,
            "permission_type_id": permission_type_one_id,
        },
    )
    assert relation_response.status_code == 200
    relation_one = relation_response.get_json()["relation"]
    assert relation_one["api_key_id"] == api_key_id
    assert relation_one["permission_type_id"] == permission_type_one_id

    bulk_response = client.post(
        "/api-key/permissions/add/many",
        headers=headers,
        json={
            "api_key_id": api_key_id,
            "permission_type_ids": [
                permission_type_two_id,
                permission_type_three_id,
            ],
        },
    )
    assert bulk_response.status_code == 200
    created_relations = bulk_response.get_json()["relations"]
    assert len(created_relations) == 2

    relations_response = client.get(
        "/api-key/permissions/all",
        headers=headers,
        query_string={"api_key_id": api_key_id},
    )
    assert relations_response.status_code == 200
    relations = relations_response.get_json()["relations"]
    assert len(relations) == 3

    view_response = client.get(
        f"/api-key/permissions/{relation_one['id']}/view", headers=headers
    )
    assert view_response.status_code == 200
    assert view_response.get_json()["relation"] == relation_one

    delete_response = client.delete(
        f"/api-key/permissions/{relation_one['id']}/delete", headers=headers
    )
    assert delete_response.status_code == 200
    assert delete_response.get_json() == {
        "msg": "Relation deleted successfully",
        "id": relation_one["id"],
    }

    bulk_delete_response = client.delete(
        "/api-key/permissions/delete/many",
        headers=headers,
        json={
            "relation_ids": [relation["id"] for relation in created_relations],
        },
    )
    assert bulk_delete_response.status_code == 200
    assert bulk_delete_response.get_json()["deleted_count"] == 2

    final_relations_response = client.get(
        "/api-key/permissions/all",
        headers=_auth_headers(jwt_token_admin),
        query_string={"api_key_id": api_key_id},
    )
    assert final_relations_response.status_code == 200
    assert final_relations_response.get_json()["relations"] == []


def test_api_key_permission_relation_endpoints_reject_invalid_uuid(
    client, jwt_token_admin
):
    headers = _auth_headers(jwt_token_admin)

    invalid_view_response = client.get(
        "/api-key/not-a-uuid/view", headers=headers
    )
    assert invalid_view_response.status_code == 400
    assert invalid_view_response.get_json()["msg"] == "Invalid API key ID format"

    invalid_delete_response = client.delete(
        "/api-key/not-a-uuid/delete", headers=headers
    )
    assert invalid_delete_response.status_code == 400
    assert invalid_delete_response.get_json()["msg"] == "Invalid API key ID format"

    invalid_relation_response = client.post(
        "/api-key/permissions/add",
        headers=headers,
        json={
            "api_key_id": "not-a-uuid",
            "permission_type_id": "still-not-a-uuid",
        },
    )
    assert invalid_relation_response.status_code == 400
    assert invalid_relation_response.get_json()["msg"] == "Invalid UUID format"


def test_api_key_permission_relation_endpoints_reject_duplicate_relation(
    client, jwt_token_admin, db_session
):
    headers = _auth_headers(jwt_token_admin)
    api_key_id = _create_api_key(client, headers, f"api-key-{uuid4().hex[:12]}")[
        "api_key_id"
    ]

    permission_type = PermissionTypes(
        permission_type_id=uuid4(),
        code=f"api-key-test-{uuid4().hex[:8]}",
        description="Duplicate relation test",
    )
    db_session.add(permission_type)
    permission_type_id = str(permission_type.permission_type_id)
    db_session.commit()

    first_relation_response = client.post(
        "/api-key/permissions/add",
        headers=headers,
        json={"api_key_id": api_key_id, "permission_type_id": permission_type_id},
    )
    assert first_relation_response.status_code == 200

    duplicate_relation_response = client.post(
        "/api-key/permissions/add",
        headers=headers,
        json={"api_key_id": api_key_id, "permission_type_id": permission_type_id},
    )
    assert duplicate_relation_response.status_code == 409
    assert (
        duplicate_relation_response.get_json()["msg"]
        == "Relation already exists or foreign key is invalid"
    )


def test_api_key_permission_relation_bulk_add_rejects_duplicate_relation(
    client, jwt_token_admin, db_session
):
    headers = _auth_headers(jwt_token_admin)
    api_key_id = _create_api_key(client, headers, f"api-key-{uuid4().hex[:12]}")[
        "api_key_id"
    ]

    permission_type_existing = PermissionTypes(
        permission_type_id=uuid4(),
        code=f"api-key-test-{uuid4().hex[:8]}",
        description="Existing relation",
    )
    permission_type_new = PermissionTypes(
        permission_type_id=uuid4(),
        code=f"api-key-test-{uuid4().hex[:8]}",
        description="New relation",
    )
    db_session.add_all([permission_type_existing, permission_type_new])
    permission_type_existing_id = str(permission_type_existing.permission_type_id)
    permission_type_new_id = str(permission_type_new.permission_type_id)
    db_session.commit()

    first_response = client.post(
        "/api-key/permissions/add",
        headers=headers,
        json={
            "api_key_id": api_key_id,
            "permission_type_id": permission_type_existing_id,
        },
    )
    assert first_response.status_code == 200

    bulk_duplicate_response = client.post(
        "/api-key/permissions/add/many",
        headers=headers,
        json={
            "api_key_id": api_key_id,
            "permission_type_ids": [
                permission_type_existing_id,
                permission_type_new_id,
            ],
        },
    )
    assert bulk_duplicate_response.status_code == 409
    assert (
        bulk_duplicate_response.get_json()["msg"]
        == "One or more relations already exist or foreign keys are invalid"
    )


def test_api_key_permission_relation_bulk_delete_rejects_invalid_uuid(
    client, jwt_token_admin, db_session
):
    headers = _auth_headers(jwt_token_admin)
    api_key_id = _create_api_key(client, headers, f"api-key-{uuid4().hex[:12]}")[
        "api_key_id"
    ]
    permission_type = PermissionTypes(
        permission_type_id=uuid4(),
        code=f"api-key-test-{uuid4().hex[:8]}",
        description="Delete test",
    )
    db_session.add(permission_type)
    permission_type_id = str(permission_type.permission_type_id)
    db_session.commit()

    relation_response = client.post(
        "/api-key/permissions/add",
        headers=headers,
        json={
            "api_key_id": api_key_id,
            "permission_type_id": permission_type_id,
        },
    )
    assert relation_response.status_code == 200

    bulk_delete_response = client.delete(
        "/api-key/permissions/delete/many",
        headers=headers,
        json={"relation_ids": ["not-a-uuid"]},
    )
    assert bulk_delete_response.status_code == 400
    assert bulk_delete_response.get_json()["msg"] == "Invalid UUID format"


def test_api_key_permission_types_all_rejects_invalid_sort_order(
    client, jwt_token_admin, db_session
):
    headers = _auth_headers(jwt_token_admin)
    permission_type = PermissionTypes(
        permission_type_id=uuid4(),
        code=f"api-key-test-{uuid4().hex[:8]}",
        description="Sort order test",
    )
    db_session.add(permission_type)
    db_session.commit()

    response = client.get(
        "/api-key/permission-types/all",
        headers=headers,
        query_string={"sort_order": "invalid"},
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert "sort_order" in payload["msg"]
