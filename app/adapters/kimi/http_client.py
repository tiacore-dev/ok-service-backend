from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from app.domain.kimi import KimiConfigurationError, KimiRequestError
from app.use_cases.kimi import KimiClient


@dataclass(slots=True)
class HTTPKimiClient(KimiClient):
    api_key: str | None
    model: str | None
    base_url: str | None
    timeout: float = 30.0

    def extract_file_content(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> str:
        response = self._post_file(
            filename=filename,
            content=content,
            content_type=content_type,
        )
        payload = self._json(response)
        file_id = payload.get("id")
        if not isinstance(file_id, str) or not file_id:
            raise KimiRequestError("Kimi API returned an invalid file response")

        primary_error: BaseException | None = None
        try:
            content_response = self._get(f"/v1/files/{file_id}/content")
            return content_response.text
        except BaseException as error:
            primary_error = error
            raise
        finally:
            try:
                self._delete(f"/v1/files/{file_id}")
            except KimiRequestError:
                if primary_error is None:
                    raise

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        developer_prompt: str | None = None,
    ) -> str:
        messages = []
        if developer_prompt is not None:
            messages.append({"role": "developer", "content": developer_prompt})
        messages.extend(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        response = self._post_json(
            "/v1/chat/completions",
            {
                "model": self._require_model(),
                "messages": messages,
            },
        )
        payload = self._json(response)
        try:
            content = payload["choices"][0]["message"]["content"]
        except (IndexError, KeyError, TypeError):
            raise KimiRequestError("Kimi API returned an invalid completion response")
        if not isinstance(content, str):
            raise KimiRequestError("Kimi API returned an invalid completion response")
        return content

    def _post_file(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str | None,
    ) -> requests.Response:
        try:
            response = requests.post(
                self._url("/v1/files"),
                headers=self._headers(),
                timeout=self.timeout,
                data={"purpose": "file-extract"},
                files={
                    "file": (
                        filename,
                        content,
                        content_type or "application/octet-stream",
                    )
                },
            )
        except requests.RequestException as error:
            raise KimiRequestError("Kimi API request failed") from error
        return self._require_success(response)

    def _post_json(
        self, path: str, payload: dict[str, object]
    ) -> requests.Response:
        try:
            response = requests.post(
                self._url(path),
                headers=self._headers(),
                timeout=self.timeout,
                json=payload,
            )
        except requests.RequestException as error:
            raise KimiRequestError("Kimi API request failed") from error
        return self._require_success(response)

    def _get(self, path: str) -> requests.Response:
        try:
            response = requests.get(
                self._url(path), headers=self._headers(), timeout=self.timeout
            )
        except requests.RequestException as error:
            raise KimiRequestError("Kimi API request failed") from error
        return self._require_success(response)

    def _delete(self, path: str) -> None:
        try:
            response = requests.delete(
                self._url(path), headers=self._headers(), timeout=self.timeout
            )
        except requests.RequestException as error:
            raise KimiRequestError("Kimi API request failed") from error
        self._require_success(response)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._require_api_key()}"}

    def _url(self, path: str) -> str:
        return f"{self._require_base_url()}{path}"

    def _require_success(self, response: requests.Response) -> requests.Response:
        if not response.ok:
            raise KimiRequestError("Kimi API request failed")
        return response

    def _require_api_key(self) -> str:
        if not self.api_key:
            raise KimiConfigurationError("MOONSHOT_API_KEY must be configured")
        return self.api_key

    def _require_model(self) -> str:
        if not self.model:
            raise KimiConfigurationError("MOONSHOT_MODEL must be configured")
        return self.model

    def _require_base_url(self) -> str:
        if not self.base_url:
            raise KimiConfigurationError("MOONSHOT_URL must be configured")
        return self.base_url.rstrip("/")

    def _json(self, response: requests.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as error:
            raise KimiRequestError(
                "Kimi API returned an invalid JSON response"
            ) from error
        if not isinstance(payload, dict):
            raise KimiRequestError("Kimi API returned an invalid JSON response")
        return payload
