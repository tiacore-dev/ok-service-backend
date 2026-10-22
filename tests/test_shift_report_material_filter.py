from uuid import uuid4

import pytest
from marshmallow import ValidationError

from app.schemas.shift_report_material_schemas import ShiftReportMaterialFilterSchema


@pytest.mark.parametrize("value", [str(uuid4()), "", "invalid", None])
@pytest.mark.parametrize("with_new_filter", [False, True])
def test_removed_material_filter_is_rejected(value, with_new_filter):
    data = {"material": value}
    if with_new_filter:
        data["project_material"] = str(uuid4())
    with pytest.raises(ValidationError) as error:
        ShiftReportMaterialFilterSchema().load(data)
    assert error.value.messages == {
        "material": ["Filter 'material' was removed; use 'project_material'."]
    }


def test_project_material_filter_and_pagination_are_preserved():
    project_material_id = uuid4()
    result = ShiftReportMaterialFilterSchema().load(
        {
            "project_material": str(project_material_id),
            "limit": "10",
            "offset": "2",
        }
    )
    assert isinstance(result, dict)
    assert result == {"project_material": project_material_id, "limit": 10, "offset": 2}


def test_other_unknown_filters_keep_existing_exclusion_behavior():
    result = ShiftReportMaterialFilterSchema().load({"unknown": "ignored"})
    assert result == {"offset": 0, "limit": 1000}
