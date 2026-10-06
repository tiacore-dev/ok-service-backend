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
        self,
        system_setting_id: str,
        *,
        value: str | None,
        value_is_set: bool,
        name: str | None,
        name_is_set: bool,
        modified_by: UUID,
    ) -> SystemSetting | None:
        record = normalize_result(
            self.manager.update(
                system_setting_id,
                value=value,
                value_is_set=value_is_set,
                name=name,
                name_is_set=name_is_set,
                modified_by=modified_by,
            )
        )
        return system_setting_dict_to_entity(record) if record is not None else None
