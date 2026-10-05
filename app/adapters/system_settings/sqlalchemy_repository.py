from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
from app.database.managers.system_settings_manager import SystemSettingsManager
from app.domain.system_settings import SystemSetting
from app.use_cases.system_settings.ports import SystemSettingRepository

from .mappers import system_setting_dict_to_entity


@dataclass(slots=True)
class SQLAlchemySystemSettingRepository(SystemSettingRepository):
    manager: SystemSettingsManager = field(default_factory=SystemSettingsManager)

    def list_system_settings(self) -> list[SystemSetting]:
        result = []
        for record in self.manager.get_all():
            normalized = normalize_result(record)
            if normalized is not None:
                result.append(system_setting_dict_to_entity(normalized))
        return result

    def get_system_setting(self, system_setting_id: str) -> SystemSetting | None:
        record = normalize_result(self.manager.get_by_id(system_setting_id))
        return system_setting_dict_to_entity(record) if record is not None else None

    def update_system_setting(
        self, system_setting_id: str, value: str | None, modified_by: UUID
    ) -> SystemSetting | None:
        record = normalize_result(
            self.manager.update_value(system_setting_id, value, modified_by)
        )
        return system_setting_dict_to_entity(record) if record is not None else None
