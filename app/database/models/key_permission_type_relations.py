from uuid import uuid4

from sqlalchemy import UUID, Column, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.db_setup import Base


class KeyPermissionTypeRelations(Base):
    __tablename__ = "key_permission_type_relations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    api_key_id = Column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.api_key_id", ondelete="CASCADE"),
        nullable=False,
    )
    permission_type_id = Column(
        UUID(as_uuid=True),
        ForeignKey("permission_types.permission_type_id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "api_key_id",
            "permission_type_id",
            name="uq_key_permission_type_relations_api_key_permission",
        ),
    )

    api_key = relationship("ApiKeys", back_populates="permissions")
    permission_type = relationship(
        "PermissionTypes", back_populates="key_permission_type_relations"
    )

    def __repr__(self):
        return (
            f"<KeyPermissionTypeRelations(id={self.id}, api_key_id={self.api_key_id}, "
            f"permission_type_id={self.permission_type_id})>"
        )

    def to_dict(self):
        return {
            "id": str(self.id),
            "api_key_id": str(self.api_key_id),
            "permission_type_id": str(self.permission_type_id),
        }
