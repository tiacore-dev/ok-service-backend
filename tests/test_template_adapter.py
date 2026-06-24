from app.adapters.template_generation import HTTPTemplateGenerator
from app.use_cases.template_generation import TemplateGenerateCommand


class _Response:
    def __init__(self, ok: bool, content: bytes):
        self.ok = ok
        self.content = content


def test_http_template_generator_posts_normalized_payload(monkeypatch):
    seen: dict[str, object] = {}

    def fake_post(*, url, json):
        seen["url"] = url
        seen["json"] = json
        return _Response(True, b"doc-bytes")

    monkeypatch.setattr(
        "app.adapters.template_generation.http_client.requests.post", fake_post
    )

    generator = HTTPTemplateGenerator(service_url="https://template.test/generate")
    command = TemplateGenerateCommand(
        url=None,
        file_name="invoice.docx",
        name="Invoice",
        is_pdf=True,
        document_data={"amount": 10},
    )

    result = generator.generate(command)

    assert result == b"doc-bytes"
    assert seen["url"] == "https://template.test/generate"
    assert seen["json"] == {
        "name": "Invoice",
        "is_pdf": True,
        "document_data": {"amount": 10},
        "file_name": "invoice.docx",
    }
