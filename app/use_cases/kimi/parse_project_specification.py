import json
from dataclasses import dataclass
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
        system_prompt = self.system_settings.get_system_setting("system_prompt")
        if (
            system_prompt is None
            or system_prompt.value is None
            or not system_prompt.value.strip()
        ):
            raise SystemPromptMissingError("Отсутствует системный промпт")
        developer_prompt = self.system_settings.get_system_setting(
            "developer_system_prompt"
        )
        if (
            developer_prompt is None
            or developer_prompt.value is None
            or not developer_prompt.value.strip()
        ):
            raise SystemPromptMissingError("Отсутствует системный промпт разработчика")
        extracted_content = self.client.extract_file_content(
            filename=filename, content=content, content_type=content_type
        )
        response = self.client.complete(
            system_prompt=system_prompt.value,
            developer_prompt=developer_prompt.value,
            reasoning_effort="low",
            response_format={"type": "json_object"},
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
        unresolved_items = payload.get("unresolved_items")
        if (
            not isinstance(works, list)
            or not isinstance(materials, list)
            or not isinstance(unresolved_items, list)
        ):
            raise KimiRequestError("Kimi API returned invalid project specification")
        work_ids: dict[str, str] = {}
        for work in works:
            if not isinstance(work, dict) or not isinstance(
                work.get("project_work_id"), str
            ):
                raise KimiRequestError(
                    "Kimi API returned invalid project specification"
                )
            placeholder = work["project_work_id"]
            if placeholder in work_ids:
                raise KimiRequestError("Kimi API returned duplicate work placeholder")
            work_ids[placeholder] = str(uuid4())
            work["project_work_id"] = work_ids[placeholder]
        for material in materials:
            if not isinstance(material, dict) or not isinstance(
                material.get("project_material_id"), str
            ):
                raise KimiRequestError(
                    "Kimi API returned invalid project specification"
                )
            material["project_material_id"] = str(uuid4())
            project_work = material.get("project_work")
            if project_work is not None:
                if not isinstance(project_work, str) or project_work not in work_ids:
                    raise KimiRequestError("Kimi API returned unknown work placeholder")
                material["project_work"] = work_ids[project_work]
        for unresolved_item in unresolved_items:
            self._assign_unresolved_item_work_id(unresolved_item, work_ids)
        return payload

    @staticmethod
    def _assign_unresolved_item_work_id(
        unresolved_item: object, work_ids: dict[str, str]
    ) -> None:
        if not isinstance(unresolved_item, dict):
            raise KimiRequestError("Kimi API returned invalid unresolved item")
        kind = unresolved_item.get("kind")
        name = unresolved_item.get("name")
        quantity = unresolved_item.get("quantity")
        price = unresolved_item.get("price")
        reason = unresolved_item.get("reason")
        if (
            not isinstance(kind, str)
            or kind not in {"work", "material"}
            or not isinstance(name, str)
            or not name.strip()
            or isinstance(quantity, bool)
            or not isinstance(quantity, (int, float))
            or isinstance(price, bool)
            or (price is not None and not isinstance(price, (int, float)))
            or not isinstance(reason, str)
            or not reason.strip()
            or "project_work" not in unresolved_item
        ):
            raise KimiRequestError("Kimi API returned invalid unresolved item")
        project_work = unresolved_item.get("project_work")
        if kind == "work":
            if project_work is not None:
                raise KimiRequestError("Kimi API returned invalid unresolved item")
            return
        if project_work is None:
            return
        if not isinstance(project_work, str) or project_work not in work_ids:
            raise KimiRequestError("Kimi API returned unknown work placeholder")
        unresolved_item["project_work"] = work_ids[project_work]
