import pytest
import requests

from app.adapters.template_generation import HTTPTemplateGenerator
from app.domain.template_generation import TemplateGenerationError
from app.use_cases.template_generation.dto import TemplateGenerateCommand


class FakeResponse:
    def __init__(self, status=200, headers=None):
        self.status_code = status
        self.headers = headers or {}
        self.closed = False
        self.iterated = False

    def iter_content(self, chunk_size):
        self.iterated = True
        assert chunk_size == 64 * 1024
        yield b"first"
        yield b"second"

    def close(self):
        self.closed = True

    @property
    def content(self):
        raise AssertionError("Must stream the response, never buffer response.content")


def command():
    return TemplateGenerateCommand(
        url="https://signed.test/file",
        name="Отчёт",
        is_pdf=True,
        is_horizontal=True,
        document_data={"works": []},
        content_type="application/pdf",
        filename="Отчёт.pdf",
    )


def test_http_template_generator_streams_payload_headers_and_cleanup(monkeypatch):
    response = FakeResponse(
        headers={
            "Content-Type": "application/pdf",
            "Content-Disposition": "attachment; filename=result.pdf",
        }
    )
    seen = {}

    def post(**kwargs):
        seen.update(kwargs)
        return response

    monkeypatch.setattr(
        "app.adapters.template_generation.http_client.requests.post", post
    )
    result = HTTPTemplateGenerator(
        "https://template.test/api/docs/generate", "secret"
    ).generate(command())
    assert not response.iterated
    assert seen == {
        "url": "https://template.test/api/docs/generate",
        "json": {
            "url": "https://signed.test/file",
            "name": "Отчёт",
            "is_pdf": True,
            "is_horizontal": True,
            "document_data": {"works": []},
        },
        "headers": {"x-api-key": "secret"},
        "timeout": 30,
        "stream": True,
    }
    assert result.content_disposition == "attachment; filename=result.pdf"
    assert list(result.chunks) == [b"first", b"second"]
    assert response.closed


def test_http_response_can_close_without_consumption_and_has_unicode_fallback(
    monkeypatch,
):
    response = FakeResponse()
    monkeypatch.setattr(
        "app.adapters.template_generation.http_client.requests.post",
        lambda **kwargs: response,
    )
    result = HTTPTemplateGenerator("https://test").generate(command())
    assert result.content_type == "application/pdf"
    assert "filename*=UTF-8''%D0" in result.content_disposition
    result.close()
    assert response.closed


@pytest.mark.parametrize("status", [201, 400, 401, 500])
def test_http_errors_close_response(monkeypatch, status):
    response = FakeResponse(status)
    monkeypatch.setattr(
        "app.adapters.template_generation.http_client.requests.post",
        lambda **kwargs: response,
    )
    with pytest.raises(TemplateGenerationError):
        HTTPTemplateGenerator("https://test").generate(command())
    assert response.closed


def test_transport_error(monkeypatch):
    def post(**kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(
        "app.adapters.template_generation.http_client.requests.post", post
    )
    with pytest.raises(TemplateGenerationError):
        HTTPTemplateGenerator("https://test").generate(command())


def test_missing_service_url():
    with pytest.raises(TemplateGenerationError):
        HTTPTemplateGenerator(None).generate(command())
