from typing import Any
from uuid import UUID

from app.domain.system_settings import SystemSetting


def system_setting_dict_to_entity(payload: dict[str, Any]) -> SystemSetting:
    return SystemSetting(
        system_setting_id=str(payload["system_setting_id"]),
        name=str(payload["name"]),
        value=payload.get("value"),
        modified_at=payload.get("modified_at"),
        modified_by=(
            UUID(str(payload["modified_by"]))
            if payload.get("modified_by")
            else None
        ),
    )


def system_setting_entity_to_response(setting: SystemSetting) -> dict[str, Any]:
    return {
        "system_setting_id": setting.system_setting_id,
        "name": setting.name,
        "value": setting.value,
        "modified_at": setting.modified_at,
        "modified_by": str(setting.modified_by) if setting.modified_by else None,
    }
