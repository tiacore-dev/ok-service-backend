from sqlalchemy.dialects.postgresql import insert
from uuid import UUID

from app.database import db_globals
from app.database.managers.abstract_manager import BaseDBManager
from app.database.models.system_settings import SystemSettings
from app.database.time_utils import utc_epoch_milliseconds


class SystemSettingsManager(BaseDBManager):
    @property
    def model(self):
        return SystemSettings

    def ensure_system_prompt(self) -> None:
        session_factory = db_globals.Session
        if session_factory is None:
            raise RuntimeError("Database session is not initialized")
        with self.session_scope() as session:
            statement = insert(self.model).values(
                system_setting_id="system_prompt", name="Системный промпт", value=None
            )
            session.execute(
                statement.on_conflict_do_nothing(
                    index_elements=["system_setting_id"]
                )
            )

    def update(
        self,
        setting_id: str,
        *,
        value: str | None,
        value_is_set: bool,
        name: str | None,
        name_is_set: bool,
        modified_by: UUID,
    ):
        with self.session_scope() as session:
            record = (
                session.query(self.model)
                .filter(self.model.system_setting_id == setting_id)
                .first()
            )
            if record is None:
                return None
            if value_is_set:
                record.value = value
            if name_is_set:
                if name is None:
                    raise ValueError("System setting name cannot be null")
                record.name = name
            record.modified_at = utc_epoch_milliseconds()
            record.modified_by = modified_by
            session.flush()
            return record.to_dict()
