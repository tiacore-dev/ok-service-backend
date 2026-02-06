from uuid import UUID, uuid4


def test_get_project_stats_by_project_materials(
    client,
    jwt_token_leader,
    db_session,
    seed_project_own,
    seed_work,
    seed_user,
    seed_work_material_relation,
    seed_work_material_relation_pcs,
):
    from app.database.managers.shift_reports_managers import ShiftReportsDetailsManager
    from app.database.models import ShiftReports

    data = {
        "project": seed_project_own["project_id"],
        "project_work_name": "Test project_work",
        "work": seed_work["work_id"],
        "quantity": 10.0,
        "summ": 0.0,
        "signed": False,
    }
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    response = client.post("/project_works/add", json=data, headers=headers)

    assert response.status_code == 200
    project_work_id = response.json["project_work_id"]

    shift_report_id = uuid4()
    report = ShiftReports(
        shift_report_id=shift_report_id,
        user=UUID(seed_user["user_id"]),
        date=20240101,
        date_start=20240101,
        date_end=20240101,
        project=UUID(seed_project_own["project_id"]),
        created_by=UUID(seed_user["user_id"]),
        signed=True,
        deleted=False,
    )
    db_session.add(report)
    db_session.commit()

    details_manager = ShiftReportsDetailsManager()
    details_manager.add_shift_report_deatails(
        created_by=seed_user["user_id"],
        shift_report=str(shift_report_id),
        project_work=str(project_work_id),
        work=seed_work["work_id"],
        quantity=5.0,
    )

    response = client.get(
        f"/projects/{str(seed_project_own['project_id'])}/get-stat-by-project-materials",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json["msg"] == "Project stats fetched successfully"

    stats = response.json["stats"]
    material_id = seed_work_material_relation["material"]
    material_pcs_id = seed_work_material_relation_pcs["material"]

    assert material_id in stats
    assert material_pcs_id in stats

    assert stats[material_id]["project_material_quantity"] == 10.0 * float(
        seed_work_material_relation["quantity"]
    )
    assert stats[material_id]["shift_report_materials_quantity"] == 5.0 * float(
        seed_work_material_relation["quantity"]
    )

    assert stats[material_pcs_id]["project_material_quantity"] == int(
        10.0 * float(seed_work_material_relation_pcs["quantity"])
    )
    assert stats[material_pcs_id]["shift_report_materials_quantity"] == int(
        5.0 * float(seed_work_material_relation_pcs["quantity"])
    )
