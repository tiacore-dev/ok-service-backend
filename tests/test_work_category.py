import pytest


@pytest.fixture
def works_categories_manager(db_session):
    from app.database.managers.works_managers import WorkCategoriesManager

    return WorkCategoriesManager(session=db_session)  # type: ignore


def test_add_work_category(client, jwt_token, db_session):
    """
    Тест на добавление новой категории работы через API.
    """
    from app.database.models import WorkCategories

    data = {"name": "New Work Category"}
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.post("/work_categories/add", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New work category added successfully"

    # Проверяем, что категория добавлена в базу данных
    category = (
        db_session.query(WorkCategories).filter_by(name="New Work Category").first()
    )
    assert category is not None
    assert str(category.work_category_id) == response.json["work_category_id"]
    assert category.name == "New Work Category"


def test_view_work_category(client, jwt_token, seed_work_category):
    """
    Тест на просмотр данных категории работы через API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get(
        f"/work_categories/{str(seed_work_category['work_category_id'])}/view",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json["msg"] == "Work category found successfully"

    # Проверяем данные категории из ответа
    category_data = response.json["work_category"]
    assert category_data["work_category_id"] == str(
        seed_work_category["work_category_id"]
    )
    assert category_data["name"] == seed_work_category["name"]


def test_soft_delete_work_category(client, jwt_token, seed_work_category, db_session):
    """
    Тест на мягкое удаление категории работы через API.
    """
    from app.database.models import WorkCategories

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/work_categories/{str(seed_work_category['work_category_id'])}/delete/soft",
        headers=headers,
    )

    assert response.status_code == 200
    assert (
        response.json["msg"]
        == f"Work category {
            seed_work_category['work_category_id']
        } soft deleted successfully"
    )

    # Проверяем, что категория помечена как удаленная в базе данных
    category = (
        db_session.query(WorkCategories)
        .filter_by(work_category_id=seed_work_category["work_category_id"])
        .first()
    )
    assert category is not None
    assert category.deleted is True


def test_hard_delete_work_category(client, jwt_token, seed_work_category, db_session):
    """
    Тест на жесткое удаление категории работы через API.
    """
    from app.database.models import WorkCategories

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.delete(
        f"/work_categories/{str(seed_work_category['work_category_id'])}/delete/hard",
        headers=headers,
    )

    assert response.status_code == 200
    assert (
        response.json["msg"]
        == f"Work category {
            seed_work_category['work_category_id']
        } hard deleted successfully"
    )

    # Проверяем, что категория удалена из базы данных
    category = (
        db_session.query(WorkCategories)
        .filter_by(work_category_id=seed_work_category["work_category_id"])
        .first()
    )
    assert category is None


def test_edit_work_category(client, jwt_token, seed_work_category, db_session):
    """
    Тест на редактирование данных категории работы через API.
    """
    from app.database.models import WorkCategories

    data = {"name": "Updated Work Category"}
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/work_categories/{str(seed_work_category['work_category_id'])}/edit",
        json=data,
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json["msg"] == "Work category edited successfully"

    # Проверяем, что данные категории обновлены в базе данных
    category = (
        db_session.query(WorkCategories)
        .filter_by(work_category_id=seed_work_category["work_category_id"])
        .first()
    )
    assert category is not None
    assert category.name == "Updated Work Category"


def test_get_all_work_categories(client, jwt_token, seed_work_category):
    """
    Тест на получение всех категорий работ через API с фильтрацией.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get("/work_categories/all", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Work categories found successfully"

    categories = response.json["work_categories"]
    assert len(categories) > 0

    # Проверяем, что созданная категория присутствует в списке
    category_data = next(
        (
            c
            for c in categories
            if c["work_category_id"] == str(seed_work_category["work_category_id"])
        ),
        None,
    )
    assert category_data is not None
    assert category_data["name"] == seed_work_category["name"]


# --- hierarchy ----------------------------------------------------------------


def _add_category(client, headers, name, parent_id=None):
    payload = {"name": name}
    if parent_id is not None:
        payload["parent_id"] = parent_id
    return client.post("/work_categories/add", json=payload, headers=headers)


def test_add_root_category_has_null_parent(client, jwt_token):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    created = _add_category(client, headers, "Root category")
    assert created.status_code == 200

    response = client.get(
        f"/work_categories/{created.json['work_category_id']}/view", headers=headers
    )

    assert response.status_code == 200
    assert response.json["work_category"]["parent_id"] is None


def test_add_nested_categories(client, jwt_token, seed_work_category, db_session):
    from app.database.models import WorkCategories

    headers = {"Authorization": f"Bearer {jwt_token}"}
    root_id = str(seed_work_category["work_category_id"])

    child = _add_category(client, headers, "Child", root_id)
    assert child.status_code == 200
    grandchild = _add_category(
        client, headers, "Grandchild", child.json["work_category_id"]
    )
    assert grandchild.status_code == 200

    record = (
        db_session.query(WorkCategories)
        .filter_by(work_category_id=grandchild.json["work_category_id"])
        .one()
    )
    assert str(record.parent_id) == child.json["work_category_id"]

    view = client.get(
        f"/work_categories/{child.json['work_category_id']}/view", headers=headers
    )
    assert view.json["work_category"]["parent_id"] == root_id


def test_add_category_with_unknown_parent_rejected(client, jwt_token):
    from uuid import uuid4

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = _add_category(client, headers, "Orphan", str(uuid4()))

    assert response.status_code == 400


def test_add_category_with_malformed_parent_rejected(client, jwt_token):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = _add_category(client, headers, "Orphan", "not-a-uuid")

    assert response.status_code == 400


def test_edit_parent_and_move_back_to_root(client, jwt_token, seed_work_category):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    root_id = str(seed_work_category["work_category_id"])
    other = _add_category(client, headers, "Other").json["work_category_id"]

    moved = client.patch(
        f"/work_categories/{other}/edit", json={"parent_id": root_id}, headers=headers
    )
    assert moved.status_code == 200
    view = client.get(f"/work_categories/{other}/view", headers=headers)
    assert view.json["work_category"]["parent_id"] == root_id

    renamed = client.patch(
        f"/work_categories/{other}/edit", json={"name": "Renamed"}, headers=headers
    )
    assert renamed.status_code == 200
    view = client.get(f"/work_categories/{other}/view", headers=headers)
    assert view.json["work_category"]["parent_id"] == root_id

    to_root = client.patch(
        f"/work_categories/{other}/edit", json={"parent_id": None}, headers=headers
    )
    assert to_root.status_code == 200
    view = client.get(f"/work_categories/{other}/view", headers=headers)
    assert view.json["work_category"]["parent_id"] is None


def test_edit_self_parent_rejected(client, jwt_token, seed_work_category):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    category_id = str(seed_work_category["work_category_id"])

    response = client.patch(
        f"/work_categories/{category_id}/edit",
        json={"parent_id": category_id},
        headers=headers,
    )

    assert response.status_code == 400


def test_edit_indirect_cycle_rejected(client, jwt_token, seed_work_category, db_session):
    from app.database.models import WorkCategories

    headers = {"Authorization": f"Bearer {jwt_token}"}
    a = str(seed_work_category["work_category_id"])
    b = _add_category(client, headers, "B", a).json["work_category_id"]
    c = _add_category(client, headers, "C", b).json["work_category_id"]

    response = client.patch(
        f"/work_categories/{a}/edit", json={"parent_id": c}, headers=headers
    )

    assert response.status_code == 400
    assert "circular" in response.json["msg"]
    db_session.expire_all()
    record = db_session.query(WorkCategories).filter_by(work_category_id=a).one()
    assert record.parent_id is None


def test_hard_delete_parent_with_children_rejected(
    client, jwt_token, seed_work_category
):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    root_id = str(seed_work_category["work_category_id"])
    assert _add_category(client, headers, "Child", root_id).status_code == 200

    response = client.delete(
        f"/work_categories/{root_id}/delete/hard", headers=headers
    )

    assert response.status_code == 409


def test_lineage_ids_returns_category_and_ancestors(db_session, seed_user):
    from uuid import uuid4

    from app.database.managers.works_managers import WorkCategoriesManager
    from app.database.models import WorkCategories

    a = WorkCategories(work_category_id=uuid4(), name="A", created_by=seed_user["user_id"])
    b = WorkCategories(
        work_category_id=uuid4(), name="B", created_by=seed_user["user_id"],
        parent_id=a.work_category_id,
    )
    c = WorkCategories(
        work_category_id=uuid4(), name="C", created_by=seed_user["user_id"],
        parent_id=b.work_category_id,
    )
    db_session.add(a)
    db_session.flush()
    db_session.add(b)
    db_session.flush()
    db_session.add(c)
    db_session.commit()

    lineage = WorkCategoriesManager(session=db_session).get_lineage_ids(
        c.work_category_id
    )

    assert set(lineage) == {a.work_category_id, b.work_category_id, c.work_category_id}
