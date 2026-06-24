from dataclasses import dataclass

from app.domain.template_generation import TemplateGenerationError
from app.use_cases.template_generation import TemplateGenerateCommand
from app.web.template_generation import routes as template_routes


@dataclass
class FakeTemplateGenerator:
    command: TemplateGenerateCommand | None = None

    def generate(self, command: TemplateGenerateCommand) -> bytes:
        self.command = command
        return b"template-bytes"


def test_template_generate_endpoint_returns_file(client, jwt_token_admin, monkeypatch):
    generator = FakeTemplateGenerator()
    monkeypatch.setattr(template_routes, "_generator", lambda: generator)

    response = client.post(
        "/templates/generate",
        headers={"Authorization": f"Bearer {jwt_token_admin}"},
        json={
            "name": "Invoice",
            "url": "https://example.test/template.docx",
            "is_pdf": False,
            "document_data": {"number": 1},
        },
    )

    assert response.status_code == 200
    assert response.data == b"template-bytes"
    assert "output.docx" in response.headers["Content-Disposition"]
    assert generator.command is not None
    assert generator.command.name == "Invoice"
    assert generator.command.url == "https://example.test/template.docx"
    assert generator.command.file_name is None


def test_template_generate_endpoint_maps_service_errors_to_500(
    client, jwt_token_admin, monkeypatch
):
    class FailingTemplateGenerator:
        def generate(self, command: TemplateGenerateCommand) -> bytes:
            raise TemplateGenerationError("boom")

    monkeypatch.setattr(
        template_routes,
        "_generator",
        lambda: FailingTemplateGenerator(),
    )

    response = client.post(
        "/templates/generate",
        headers={"Authorization": f"Bearer {jwt_token_admin}"},
        json={
            "name": "Invoice",
            "file_name": "invoice.docx",
            "document_data": {"number": 1},
        },
    )

    assert response.status_code == 500
    assert response.get_json() == {"msg": "Ошибка при генерации файла"}


def test_template_generate_endpoint_requires_body(client, jwt_token_admin):
    response = client.post(
        "/templates/generate",
        headers={"Authorization": f"Bearer {jwt_token_admin}"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"msg": "Request body is required"}
