from uuid import uuid4

from sqlalchemy import UUID, BigInteger, Column, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text as sql_text

from app.database.db_setup import Base
from app.database.time_utils import utc_epoch_milliseconds


class ShiftReportComments(Base):
    __tablename__ = "shift_report_comments"
    shift_report_comment_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    shift_report_id = Column(
        UUID(as_uuid=True),
        ForeignKey("shift_reports.shift_report_id", ondelete="CASCADE"),
        nullable=False,
    )
    text = Column(Text, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    created_at = Column(
        BigInteger,
        nullable=False,
        default=utc_epoch_milliseconds,
        server_default=sql_text("CAST(EXTRACT(EPOCH FROM NOW()) * 1000 AS BIGINT)"),
    )
    updated_at = Column(BigInteger, nullable=True)
    browser_id = Column(UUID(as_uuid=True), nullable=True)
    shift_report = relationship("ShiftReports", back_populates="comments")
    author = relationship("Users")
    attachments = relationship(
        "ShiftReportCommentAttachments",
        back_populates="comment",
        cascade="all, delete-orphan",
    )


class AcceptanceComments(Base):
    __tablename__ = "acceptance_comments"
    acceptance_comment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    acceptance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("acceptances.id", ondelete="CASCADE"),
        nullable=False,
    )
    text = Column(Text, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    created_at = Column(
        BigInteger,
        nullable=False,
        default=utc_epoch_milliseconds,
        server_default=sql_text("CAST(EXTRACT(EPOCH FROM NOW()) * 1000 AS BIGINT)"),
    )
    updated_at = Column(BigInteger, nullable=True)
    browser_id = Column(UUID(as_uuid=True), nullable=True)
    acceptance = relationship("Acceptances", back_populates="comments")
    author = relationship("Users")
    attachments = relationship(
        "AcceptanceCommentAttachments",
        back_populates="comment",
        cascade="all, delete-orphan",
    )


class ShiftReportCommentAttachments(Base):
    __tablename__ = "shift_report_comment_attachments"
    __table_args__ = (
        UniqueConstraint(
            "shift_report_comment_id",
            "attachment_id",
            name="uq_shift_report_comment_attachments",
        ),
    )
    shift_report_comment_attachment_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    shift_report_comment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("shift_report_comments.shift_report_comment_id", ondelete="CASCADE"),
        nullable=False,
    )
    attachment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("attachments.attachment_id", ondelete="CASCADE"),
        nullable=False,
    )
    comment = relationship("ShiftReportComments", back_populates="attachments")
    attachment = relationship("Attachments")


class AcceptanceCommentAttachments(Base):
    __tablename__ = "acceptance_comment_attachments"
    __table_args__ = (
        UniqueConstraint(
            "acceptance_comment_id",
            "attachment_id",
            name="uq_acceptance_comment_attachments",
        ),
    )
    acceptance_comment_attachment_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    acceptance_comment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("acceptance_comments.acceptance_comment_id", ondelete="CASCADE"),
        nullable=False,
    )
    attachment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("attachments.attachment_id", ondelete="CASCADE"),
        nullable=False,
    )
    comment = relationship("AcceptanceComments", back_populates="attachments")
    attachment = relationship("Attachments")
