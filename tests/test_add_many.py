def test_add_project_work(client, jwt_token_leader, db_session, seed_work, seed_project_own):
    """
    Тест на добавление нескольких ProjectWork через API.
    """
    from app.database.models import ProjectWorks

    data = [
        {
            "project": seed_project_own['project_id'],
            "work": seed_work["work_id"],
            "quantity": 200.0,
            "summ": 10000.0,
            "signed": False
        },
        {
            "project": seed_project_own['project_id'],
            "work": seed_work["work_id"],
            "quantity": 100.0,
            "summ": 100.0,
            "signed": False
        }
    ]
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    response = client.post("/project_works/add/many",
                           json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Project works added successfully"
    assert "project_work_ids" in response.json
    assert isinstance(response.json["project_work_ids"], list)
    assert len(response.json["project_work_ids"]) == len(data)

    # Проверяем, что все записи добавлены в базу
    for project_work_id, work_data in zip(response.json["project_work_ids"], data):
        project_work = db_session.query(ProjectWorks).filter_by(
            project_work_id=project_work_id).first()
        assert project_work is not None
        assert str(project_work.project_work_id) == project_work_id
        assert project_work.quantity == work_data["quantity"]
        assert project_work.summ == work_data["summ"]
        assert project_work.signed == work_data["signed"]
