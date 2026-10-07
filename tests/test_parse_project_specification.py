import json
from dataclasses import dataclass
from uuid import UUID

import pytest

from app.domain.kimi import KimiRequestError
from app.domain.system_settings import SystemSetting
from app.use_cases.kimi import ParseProjectSpecificationUseCase


@dataclass
class _Settings:
    value: str = "Parse the document"

    def get_system_setting(self, system_setting_id: str) -> SystemSetting:
        assert system_setting_id == "system_prompt"
        return SystemSetting("system_prompt", "Системный промпт", self.value)


class _Catalog:
    def work_catalog(self):
        return [{"id": "work-id", "name": "Монтаж"}]

    def material_catalog(self):
        return [{"id": "material-id", "name": "Бетон"}]


class _Client:
    def __init__(self, response: str):
        self.response = response
        self.user_prompt: str | None = None

    def extract_file_content(self, **kwargs) -> str:
        assert kwargs["filename"] == "specification.pdf"
        return "Document content"

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        assert system_prompt == "Parse the document"
        self.user_prompt = user_prompt
        return self.response


def test_parse_project_specification_passes_catalogs_and_replaces_placeholders():
    client = _Client(
        json.dumps(
            {
                "project_works": [
                    {
                        "project_work_id": "new-project-work-1",
                        "project_work_name": "Монтаж",
                        "work": "work-id",
                        "quantity": 2,
                        "price": None,
                    }
                ],
                "project_materials": [
                    {
                        "project_material_id": "new-project-material-1",
                        "material": "material-id",
                        "quantity": 3,
                        "price": 10,
                        "project_work": "new-project-work-1",
                    }
                ],
                "unresolved_items": [],
            }
        )
    )

    result = ParseProjectSpecificationUseCase(client, _Settings(), _Catalog()).execute(
        filename="specification.pdf", content=b"content", content_type="application/pdf"
    )

    prompt = json.loads(client.user_prompt or "{}")
    assert prompt["WORK_CATALOG"] == [{"id": "work-id", "name": "Монтаж"}]
    assert prompt["MATERIAL_CATALOG"] == [{"id": "material-id", "name": "Бетон"}]
    work_id = result["project_works"][0]["project_work_id"]
    assert str(UUID(work_id)) == work_id
    assert result["project_materials"][0]["project_work"] == work_id
    assert str(UUID(result["project_materials"][0]["project_material_id"]))


def test_parse_project_specification_rejects_unknown_work_placeholder():
    client = _Client(
        json.dumps(
            {
                "project_works": [],
                "project_materials": [
                    {
                        "project_material_id": "new-project-material-1",
                        "project_work": "new-project-work-1",
                    }
                ],
            }
        )
    )

    use_case = ParseProjectSpecificationUseCase(client, _Settings(), _Catalog())

    with pytest.raises(KimiRequestError, match="unknown work placeholder"):
        use_case.execute(
            filename="specification.pdf", content=b"content", content_type=None
        )
