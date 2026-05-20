from uuid import uuid4

from sqlalchemy import UUID, Column, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.db_setup import Base


class PermissionTypes(Base):
    __tablename__ = "permission_types"

    permission_type_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    code = Column(String, nullable=False)
    description = Column(String, nullable=True)

    __table_args__ = (UniqueConstraint("code", name="uq_permission_types_code"),)

    key_permission_type_relations = relationship(
        "KeyPermissionTypeRelations",
        back_populates="permission_type",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return (
            f"<PermissionTypes(permission_type_id={self.permission_type_id}, "
            f"code={self.code})>"
        )

    def to_dict(self):
        return {
            "permission_type_id": str(self.permission_type_id),
            "code": self.code,
            "description": self.description if self.description else None,  # type: ignore
        }
