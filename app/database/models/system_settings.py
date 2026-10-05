from sqlalchemy import BigInteger, Column, ForeignKey, Text, String

from app.database.db_setup import Base


class SystemSettings(Base):
    __tablename__ = "system_settings"

    system_setting_id = Column(String, primary_key=True, nullable=False)
    value = Column(Text, nullable=True)
    modified_at = Column(BigInteger, nullable=True)
    modified_by = Column(ForeignKey("users.user_id"), nullable=True)

    def to_dict(self):
        modified_by = self.modified_by
        return {
            "system_setting_id": self.system_setting_id,
            "value": self.value,
            "modified_at": self.modified_at,
            "modified_by": str(modified_by) if modified_by is not None else None,
        }
