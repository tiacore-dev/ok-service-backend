import pytest
from flask import Flask
from flask_restx import Api

from app.web.acceptance_comments.routes import acceptance_comment_ns
from app.web.shift_report_comments.routes import shift_comment_ns


@pytest.mark.parametrize("target", ["acceptances", "shift_reports"])
def test_comment_attachment_upload_swagger(target):
    app = Flask(__name__)
    api = Api(app)
    api.add_namespace(acceptance_comment_ns)
    api.add_namespace(shift_comment_ns)

    response = app.test_client().get("/swagger.json")

    assert response.status_code == 200
    operation = response.get_json()["paths"][
        f"/{target}/comments/{{comment_id}}/attachments"
    ]["post"]
    assert operation["consumes"] == ["multipart/form-data"]
    files = next(param for param in operation["parameters"] if param["name"] == "files")
    assert files["in"] == "formData"
    assert files["type"] == "file"
    assert files["required"] is True
    assert "repeat" in files["description"]
