def test_add_work_material_relation(client, jwt_token, seed_work, seed_material, db_session):
    from app.database.models import WorkMaterialRelations

    data = {
        "work": seed_work["work_id"],
        "material": seed_material["material_id"],
        "quantity": 3.25,
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.post(
        "/work_material_relations/add", json=data, headers=headers
    )

    assert response.status_code == 200
    assert response.json["msg"] == "Work material relation added successfully"

    relation = (
        db_session.query(WorkMaterialRelations)
        .filter_by(work=seed_work["work_id"], material=seed_material["material_id"])
        .first()
    )
    assert relation is not None
    assert str(relation.work_material_relation_id) == response.json[
        "work_material_relation_id"
    ]
    assert str(relation.work) == seed_work["work_id"]
    assert str(relation.material) == seed_material["material_id"]
    assert float(relation.quantity) == 3.25


def test_view_work_material_relation(client, jwt_token, seed_work_material_relation):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get(
        f"/work_material_relations/{str(seed_work_material_relation['work_material_relation_id'])}/view",
        headers=headers,
    )

    assert response.status_code == 200
    assert "work_material_relation" in response.json
    assert response.json["msg"] == "Work material relation found successfully"

    relation_data = response.json["work_material_relation"]
    assert relation_data["work_material_relation_id"] == str(
        seed_work_material_relation["work_material_relation_id"]
    )
    assert relation_data["work"] == str(seed_work_material_relation["work"])
    assert relation_data["material"] == str(seed_work_material_relation["material"])


def test_hard_delete_work_material_relation(
    client, jwt_token, seed_work_material_relation, db_session
):
    from app.database.models import WorkMaterialRelations

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.delete(
        f"/work_material_relations/{str(seed_work_material_relation['work_material_relation_id'])}/delete/hard",
        headers=headers,
    )

    assert response.status_code == 200
    assert (
        response.json["msg"]
        == f"Work material relation {seed_work_material_relation['work_material_relation_id']} hard deleted successfully"
    )

    relation = (
        db_session.query(WorkMaterialRelations)
        .filter_by(
            work_material_relation_id=seed_work_material_relation[
                "work_material_relation_id"
            ]
        )
        .first()
    )
    assert relation is None


def test_edit_work_material_relation(
    client, jwt_token, seed_work_material_relation, db_session
):
    from app.database.models import WorkMaterialRelations

    data = {"quantity": 7.0}
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/work_material_relations/{str(seed_work_material_relation['work_material_relation_id'])}/edit",
        json=data,
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json["msg"] == "Work material relation edited successfully"

    relation = (
        db_session.query(WorkMaterialRelations)
        .filter_by(
            work_material_relation_id=seed_work_material_relation[
                "work_material_relation_id"
            ]
        )
        .first()
    )
    assert relation is not None
    assert float(relation.quantity) == 7.0


def test_get_all_work_material_relations(
    client, jwt_token, seed_work_material_relation
):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get("/work_material_relations/all", headers=headers)

    assert response.status_code == 200
    assert "work_material_relations" in response.json
    assert response.json["msg"] == "Work material relations found successfully"

    relations = response.json["work_material_relations"]
    assert any(
        rel["work_material_relation_id"]
        == str(seed_work_material_relation["work_material_relation_id"])
        for rel in relations
    )
