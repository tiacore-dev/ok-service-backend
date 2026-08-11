from uuid import uuid4

from sqlalchemy import UUID, BigInteger, Column, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.database.db_setup import Base
from app.database.time_utils import utc_epoch_milliseconds


class Attachments(Base):
    __tablename__ = "attachments"

    attachment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    name = Column(String(255), nullable=False)
    s3_key = Column(String(512), nullable=False, unique=True)
    file_size = Column(BigInteger, nullable=False)
    checksum = Column(String(64), nullable=False)
    meta = Column(JSON, nullable=False, default=dict)
    created_at = Column(
        BigInteger,
        default=utc_epoch_milliseconds,
        server_default=text("CAST(EXTRACT(EPOCH FROM NOW()) * 1000 AS BIGINT)"),
        nullable=False,
    )
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)

    project_attachments = relationship("ProjectAttachments", back_populates="attachment")
    shift_report_attachments = relationship(
        "ShiftReportAttachments", back_populates="attachment"
    )
    object_attachments = relationship("ObjectAttachments", back_populates="attachment")
    creator = relationship("Users", back_populates="created_attachments")


class ProjectAttachments(Base):
    __tablename__ = "project_attachments"
    __table_args__ = (
        UniqueConstraint("project_id", "attachment_id", name="uq_project_attachments"),
    )

    project_attachment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.project_id"),
        nullable=False,
    )
    attachment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("attachments.attachment_id", ondelete="CASCADE"),
        nullable=False,
    )

    project = relationship("Projects", back_populates="project_attachments")
    attachment = relationship("Attachments", back_populates="project_attachments")


class ShiftReportAttachments(Base):
    __tablename__ = "shift_report_attachments"
    __table_args__ = (
        UniqueConstraint(
            "shift_report_id", "attachment_id", name="uq_shift_report_attachments"
        ),
    )

    shift_report_attachment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    shift_report_id = Column(
        UUID(as_uuid=True),
        ForeignKey("shift_reports.shift_report_id"),
        nullable=False,
    )
    attachment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("attachments.attachment_id", ondelete="CASCADE"),
        nullable=False,
    )

    shift_report = relationship("ShiftReports", back_populates="shift_report_attachments")
    attachment = relationship("Attachments", back_populates="shift_report_attachments")


class ObjectAttachments(Base):
    __tablename__ = "object_attachments"
    __table_args__ = (
        UniqueConstraint("object_id", "attachment_id", name="uq_object_attachments"),
    )

    object_attachment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    object_id = Column(
        UUID(as_uuid=True),
        ForeignKey("objects.object_id"),
        nullable=False,
    )
    attachment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("attachments.attachment_id", ondelete="CASCADE"),
        nullable=False,
    )

    object = relationship("Objects", back_populates="object_attachments")
    attachment = relationship("Attachments", back_populates="object_attachments")
