from __future__ import annotations

from typing import Any

import requests
import pytest

from app.adapters.kimi import HTTPKimiClient
from app.domain.kimi import KimiConfigurationError, KimiRequestError


class _Response:
    def __init__(self, *, payload: object | None = None, text: str = "", ok: bool = True):
        self._payload = payload
        self.text = text
        self.ok = ok

    def json(self) -> object:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _client() -> HTTPKimiClient:
    return HTTPKimiClient(
        api_key="moonshot-secret",
        model="kimi-test",
        base_url="https://api.moonshot.test/",
    )


def _patch_requests(monkeypatch, fake_request) -> None:
    for method in ("post", "get", "delete"):
        monkeypatch.setattr(
            f"app.adapters.kimi.http_client.requests.{method}",
            lambda url, *, _method=method, **kwargs: fake_request(_method, url, **kwargs),
        )


def test_extract_file_content_uploads_file_and_returns_extracted_content(monkeypatch):
    calls: list[dict[str, Any]] = []

    def fake_request(method: str, url: str, **kwargs: object) -> _Response:
        calls.append({"method": method, "url": url, **kwargs})
        if method == "post":
            return _Response(payload={"id": "file_123"})
        return _Response(text="# Extracted content")

    _patch_requests(monkeypatch, fake_request)

    result = _client().extract_file_content(
        filename="report.pdf",
        content=b"pdf-content",
        content_type="application/pdf",
    )

    assert result == "# Extracted content"
    assert calls == [
        {
            "method": "post",
            "url": "https://api.moonshot.test/v1/files",
            "headers": {"Authorization": "Bearer moonshot-secret"},
            "timeout": 30.0,
            "data": {"purpose": "file-extract"},
            "files": {"file": ("report.pdf", b"pdf-content", "application/pdf")},
        },
        {
            "method": "get",
            "url": "https://api.moonshot.test/v1/files/file_123/content",
            "headers": {"Authorization": "Bearer moonshot-secret"},
            "timeout": 30.0,
        },
        {
            "method": "delete",
            "url": "https://api.moonshot.test/v1/files/file_123",
            "headers": {"Authorization": "Bearer moonshot-secret"},
            "timeout": 30.0,
        },
    ]


def test_complete_sends_system_and_user_prompts(monkeypatch):
    seen: dict[str, object] = {}

    def fake_request(method: str, url: str, **kwargs: object) -> _Response:
        seen.update({"method": method, "url": url, **kwargs})
        return _Response(payload={"choices": [{"message": {"content": "Answer"}}]})

    _patch_requests(monkeypatch, fake_request)

    result = _client().complete(system_prompt="System prompt", user_prompt="Question")

    assert result == "Answer"
    assert seen == {
        "method": "post",
        "url": "https://api.moonshot.test/v1/chat/completions",
        "headers": {"Authorization": "Bearer moonshot-secret"},
        "timeout": 30.0,
        "json": {
            "model": "kimi-test",
            "messages": [
                {"role": "system", "content": "System prompt"},
                {"role": "user", "content": "Question"},
            ],
        },
    }


def test_complete_sends_developer_system_and_user_prompts(monkeypatch):
    seen: dict[str, object] = {}

    def fake_request(method: str, url: str, **kwargs: object) -> _Response:
        seen.update({"method": method, "url": url, **kwargs})
        return _Response(payload={"choices": [{"message": {"content": "Answer"}}]})

    _patch_requests(monkeypatch, fake_request)

    result = _client().complete(
        developer_prompt="Developer prompt",
        system_prompt="System prompt",
        user_prompt="Question",
    )

    assert result == "Answer"
    assert seen["json"] == {
        "model": "kimi-test",
        "messages": [
            {"role": "developer", "content": "Developer prompt"},
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Question"},
        ],
    }


def test_client_requires_model_for_completion():
    client = HTTPKimiClient("key", None, "https://api.moonshot.test")

    with pytest.raises(KimiConfigurationError, match="MOONSHOT_MODEL"):
        client.complete(system_prompt="System", user_prompt="Question")


def test_client_maps_transport_error(monkeypatch):
    def fake_request(*args: object, **kwargs: object) -> _Response:
        raise requests.ConnectionError()

    _patch_requests(monkeypatch, fake_request)

    with pytest.raises(KimiRequestError, match="Kimi API request failed"):
        _client().extract_file_content(filename="report.txt", content=b"content")


def test_extract_file_content_preserves_content_error_when_cleanup_fails(monkeypatch):
    calls: list[str] = []

    def fake_request(method: str, url: str, **kwargs: object) -> _Response:
        calls.append(method)
        if method == "post":
            return _Response(payload={"id": "file_123"})
        if method == "get":
            raise requests.ConnectionError()
        return _Response(ok=False)

    _patch_requests(monkeypatch, fake_request)

    with pytest.raises(KimiRequestError, match="Kimi API request failed"):
        _client().extract_file_content(filename="report.txt", content=b"content")

    assert calls == ["post", "get", "delete"]
