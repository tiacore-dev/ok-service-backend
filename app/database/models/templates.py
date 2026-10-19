from uuid import uuid4

from sqlalchemy import UUID, Boolean, Column, Enum, Index, String, Text, text

from app.database.db_setup import Base
from app.domain.templates import DEFAULT_TEMPLATE_INDEX, TemplateTypes


class Templates(Base):
    __tablename__ = "templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    template_type = Column(
        Enum(
            TemplateTypes,
            name="template_types",
            values_callable=lambda cls: [v.value for v in cls],
        ),
        nullable=False,
    )
    s3_key = Column(String(512), nullable=False, unique=True)
    file_name = Column(String(255), nullable=False)
    content_type = Column(String(255), nullable=False)
    output_file_name = Column(Text, nullable=True)
    is_horizontal = Column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_pdf = Column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_default = Column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    __table_args__ = (
        Index("ix_templates_template_type", "template_type"),
        Index(
            DEFAULT_TEMPLATE_INDEX,
            "template_type",
            unique=True,
            postgresql_where=text("is_default"),
        ),
    )
