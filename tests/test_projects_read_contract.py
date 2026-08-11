from uuid import uuid4

from app.adapters.projects import project_dict_to_response


def test_project_response_keeps_legacy_empty_name():
    project_id = uuid4()
    payload = {
        "project_id": project_id,
        "name": "   ",
        "object": uuid4(),
        "project_leader": None,
        "night_shift_available": False,
        "extreme_conditions_available": False,
        "created_by": None,
        "created_at": 1,
        "deleted": False,
    }

    result = project_dict_to_response(payload)

    assert result["project_id"] == str(project_id)
    assert result["name"] == "   "
    assert result["project_leader"] is None
    assert result["created_by"] is None
