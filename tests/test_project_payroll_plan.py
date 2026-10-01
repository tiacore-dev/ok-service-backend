from typing import cast
from uuid import uuid4

from app.adapters.projects import project_dict_to_entity, project_entity_to_response
from app.domain.projects import ProjectStatus
from app.schemas.project_schemas import ProjectCreateSchema, ProjectEditSchema


def test_project_schemas_expose_nullable_payroll_plan():
    assert "payroll_plan" in ProjectCreateSchema().fields

    data = cast(
        dict[str, object],
        ProjectEditSchema().load({"payroll_plan": 125000.50}),
    )

    assert data["payroll_plan"] == 125000.50
    cleared_data = cast(
        dict[str, object], ProjectEditSchema().load({"payroll_plan": None})
    )
    assert cleared_data["payroll_plan"] is None


def test_project_mapper_preserves_payroll_plan():
    project = project_dict_to_entity(
        {
            "project_id": str(uuid4()),
            "name": "Project",
            "object": str(uuid4()),
            "project_leader": None,
            "night_shift_available": False,
            "extreme_conditions_available": False,
            "payroll_plan": 125000.50,
            "created_by": None,
            "created_at": 1,
            "deleted": False,
            "status": ProjectStatus.PENDING.value,
        }
    )

    assert project.payroll_plan == 125000.50
    assert project_entity_to_response(project)["payroll_plan"] == 125000.50
