from dataclasses import dataclass
import json
from typing import Any
from uuid import uuid4

from app.domain.kimi import KimiRequestError, SystemPromptMissingError

from .ports import KimiClient, ProjectSpecificationCatalog, SystemPromptRepository


@dataclass(slots=True)
class ParseProjectSpecificationUseCase:
    client: KimiClient
    system_settings: SystemPromptRepository
    catalog: ProjectSpecificationCatalog

    def execute(
        self, *, filename: str, content: bytes, content_type: str | None
    ) -> dict[str, Any]:
        setting = self.system_settings.get_system_setting("system_prompt")
        if setting is None or setting.value is None or not setting.value.strip():
            raise SystemPromptMissingError("Отсутствует системный промпт")
        extracted_content = self.client.extract_file_content(
            filename=filename, content=content, content_type=content_type
        )
        response = self.client.complete(
            system_prompt=setting.value,
            user_prompt=json.dumps(
                {
                    "WORK_CATALOG": self.catalog.work_catalog(),
                    "MATERIAL_CATALOG": self.catalog.material_catalog(),
                    "DOCUMENT_CONTENT": extracted_content,
                },
                ensure_ascii=False,
            ),
        )
        return self._assign_ids(response)

    def _assign_ids(self, response: str) -> dict[str, Any]:
        try:
            payload = json.loads(response)
        except json.JSONDecodeError as error:
            raise KimiRequestError("Kimi API returned invalid JSON") from error
        if not isinstance(payload, dict):
            raise KimiRequestError("Kimi API returned invalid JSON")
        works = payload.get("project_works")
        materials = payload.get("project_materials")
        if not isinstance(works, list) or not isinstance(materials, list):
            raise KimiRequestError("Kimi API returned invalid project specification")
        work_ids: dict[str, str] = {}
        for work in works:
            if not isinstance(work, dict) or not isinstance(work.get("project_work_id"), str):
                raise KimiRequestError("Kimi API returned invalid project specification")
            placeholder = work["project_work_id"]
            if placeholder in work_ids:
                raise KimiRequestError("Kimi API returned duplicate work placeholder")
            work_ids[placeholder] = str(uuid4())
            work["project_work_id"] = work_ids[placeholder]
        for material in materials:
            if not isinstance(material, dict) or not isinstance(material.get("project_material_id"), str):
                raise KimiRequestError("Kimi API returned invalid project specification")
            material["project_material_id"] = str(uuid4())
            project_work = material.get("project_work")
            if project_work is not None:
                if not isinstance(project_work, str) or project_work not in work_ids:
                    raise KimiRequestError("Kimi API returned unknown work placeholder")
                material["project_work"] = work_ids[project_work]
        return payload
