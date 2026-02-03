

def test_add_project_work(
    client,
    jwt_token_leader,
    db_session,
    seed_work,
    seed_project_own,
    seed_work_material_relation,
    seed_work_material_relation_pcs,
):
    """
    Тест на добавление нового ProjectWork через API.
    """
    from app.database.models import ProjectMaterials, ProjectWorks

    data = {
        "project": seed_project_own['project_id'],
        "project_work_name": "Test project_work",
        "work": seed_work["work_id"],
        "quantity": 200.0,
        "summ": 10000.0,
        "signed": False
    }
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    response = client.post("/project_works/add", json=data, headers=headers)

    assert response.status_code == 200
    # assert response.json["msg"] == "New project work added successfully"

    project_work = db_session.query(ProjectWorks).filter_by(
        work=seed_work["work_id"]).first()
    assert project_work is not None
    assert str(
        project_work.project_work_id) == response.json['project_work_id']
    assert project_work.quantity == 200.0
    assert project_work.summ == 10000.0
    assert project_work.signed is False

    records = db_session.query(ProjectMaterials).filter_by(
        project_work=project_work.project_work_id
    ).all()
    assert len(records) == 2
    quantities = {str(r.material): float(r.quantity) for r in records}
    assert quantities[seed_work_material_relation["material"]] == 200.0 * float(
        seed_work_material_relation["quantity"]
    )
    assert quantities[seed_work_material_relation_pcs["material"]] == int(
        200.0 * float(seed_work_material_relation_pcs["quantity"])
    )


def test_view_project_work(client, jwt_token_leader, seed_project_work_own, seed_work):
    """
    Тест на просмотр данных ProjectWork через API.
    """
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    response = client.get(
        f"/project_works/{str(seed_project_work_own['project_work_id'])}/view", headers=headers)

    assert response.status_code == 200
    assert "project_work" in response.json
    assert response.json["msg"] == "Project work found successfully"

    project_work_data = response.json["project_work"]
    assert project_work_data["project_work_id"] == str(
        seed_project_work_own["project_work_id"])
    assert project_work_data["quantity"] == seed_project_work_own["quantity"]
    assert project_work_data["summ"] == seed_project_work_own["summ"]
    assert project_work_data["signed"] == seed_project_work_own["signed"]
    assert project_work_data["project_work_name"] == seed_project_work_own["project_work_name"]

    assert project_work_data["work"] == seed_work["work_id"]


def test_soft_delete_project_work(client, jwt_token_leader, seed_project_work_own):
    """
    Тест на мягкое удаление ProjectWork.
    """
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    response = client.patch(
        f"/project_works/{str(seed_project_work_own['project_work_id'])}/delete/soft", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"Project work {
        seed_project_work_own['project_work_id']} soft deleted successfully"
    assert response.json['project_work_id'] == seed_project_work_own['project_work_id']


def test_hard_delete_project_work(
    client,
    jwt_token_leader,
    seed_project_work_own,
    db_session,
    seed_work_material_relation,
    seed_work_material_relation_pcs,
):
    """
    Тест на жесткое удаление ProjectWork.
    """
    from app.database.models import ProjectMaterials, ProjectWorks
    from app.database.managers.projects_managers import ProjectWorksManager

    headers = {"Authorization": f"Bearer {jwt_token_leader}"}

    project_work = db_session.query(ProjectWorks).filter_by(
        project_work_id=seed_project_work_own["project_work_id"]
    ).first()
    ProjectWorksManager()._sync_project_materials(
        db_session, project_work, project_work.created_by
    )
    db_session.commit()

    records = db_session.query(ProjectMaterials).filter_by(
        project_work=seed_project_work_own["project_work_id"]
    ).all()
    assert len(records) == 2

    response = client.delete(
        f"/project_works/{str(seed_project_work_own['project_work_id'])}/delete/hard", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"Project work {
        seed_project_work_own['project_work_id']} hard deleted successfully"
    assert response.json['project_work_id'] == seed_project_work_own['project_work_id']

    project_work = db_session.query(ProjectWorks).filter_by(
        project_work_id=seed_project_work_own["project_work_id"]).first()
    assert project_work is None

    records = db_session.query(ProjectMaterials).filter_by(
        project_work=seed_project_work_own["project_work_id"]
    ).all()
    assert records == []


def test_edit_project_work(
    client,
    jwt_token_leader,
    seed_project_work_own,
    db_session,
    seed_work_material_relation,
    seed_work_material_relation_pcs,
):
    """
    Тест на редактирование данных ProjectWork через API.
    """
    from app.database.models import ProjectMaterials, ProjectWorks

    data = {
        "quantity": 300.0,
        "summ": 15000.0,
        "signed": True
    }
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    response = client.patch(
        f"/project_works/{str(seed_project_work_own['project_work_id'])}/edit", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Project work edited successfully"
    assert response.json['project_work_id'] == seed_project_work_own['project_work_id']

    project_work = db_session.query(ProjectWorks).filter_by(
        project_work_id=seed_project_work_own["project_work_id"]).first()
    assert project_work is not None
    assert project_work.quantity == 300.0
    assert project_work.summ == 15000.0
    assert project_work.signed is True

    records = db_session.query(ProjectMaterials).filter_by(
        project_work=seed_project_work_own["project_work_id"]
    ).all()
    assert len(records) == 2
    quantities = {str(r.material): float(r.quantity) for r in records}
    assert quantities[seed_work_material_relation["material"]] == 300.0 * float(
        seed_work_material_relation["quantity"]
    )
    assert quantities[seed_work_material_relation_pcs["material"]] == int(
        300.0 * float(seed_work_material_relation_pcs["quantity"])
    )


def test_get_all_project_works(client, jwt_token_leader, seed_project_work_own, seed_work):
    """
    Тест на получение списка ProjectWorks через API.
    """
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    response = client.get("/project_works/all", headers=headers)

    assert response.status_code == 200
    assert "project_works" in response.json
    assert response.json["msg"] == "Project works found successfully"

    project_works = response.json["project_works"]
    project_work_data = next((pw for pw in project_works if pw["project_work_id"] == str(
        seed_project_work_own["project_work_id"])), None)
    assert project_work_data is not None

    assert project_work_data["work"] == seed_work["work_id"]
