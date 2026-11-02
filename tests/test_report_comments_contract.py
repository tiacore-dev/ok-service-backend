from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest

import app.adapters.acceptances.repository as acceptance_repository_module
import app.adapters.shift_reports.sqlalchemy_repository as shift_repository_module
import app.use_cases.report_comments.service as report_comment_service

from app.adapters.report_comments.cleanup import CommentAttachmentCleanup
from app.database.managers.materials_manager import AcceptancesManager
from app.database.managers.shift_reports_managers import ShiftReportsManager
from app.use_cases.report_comments.service import (
    CommentActor,
    CommentError,
    ReportCommentService,
    ensure_comment_attachment_mutable,
    is_comment_editable,
)
from app.utils.api_key_permissions import API_KEY_PERMISSIONS


def test_comment_edit_window_uses_server_created_at_and_closes_after_five_minutes():
    created_at = 1_800_000_000_000
    assert is_comment_editable(created_at, created_at)
    assert is_comment_editable(created_at, created_at + 5 * 60 * 1000)
    assert not is_comment_editable(created_at, created_at + 5 * 60 * 1000 + 1)
    assert not is_comment_editable(created_at, created_at - 1)


def test_comment_endpoints_are_in_api_key_permission_catalog():
    descriptions = {description for _, description in API_KEY_PERMISSIONS}
    assert "POST /shift_reports/{shift_report_id}/comments" in descriptions
    assert "GET /shift_reports/{shift_report_id}/comments" in descriptions
    assert "PATCH /shift_reports/comments/{comment_id}" in descriptions
    assert "DELETE /shift_reports/comments/{comment_id}" in descriptions
    assert "POST /acceptances/{acceptance_id}/comments" in descriptions
    assert "GET /acceptances/{acceptance_id}/comments" in descriptions
    assert "PATCH /acceptances/comments/{comment_id}" in descriptions
    assert "DELETE /acceptances/comments/{comment_id}" in descriptions
    assert "POST /shift_reports/comments/{comment_id}/attachments" in descriptions
    assert "GET /shift_reports/comments/{comment_id}/attachments/{attachment_id}/download" in descriptions
    assert "POST /acceptances/comments/{comment_id}/attachments" in descriptions
    assert "GET /acceptances/comments/{comment_id}/attachments/{attachment_id}/download" in descriptions


class _ParticipationQuery:
    def __init__(self, participates):
        self.participates = participates

    def join(self, *_args):
        return self

    def filter(self, *_args):
        return self

    def first(self):
        return object() if self.participates else None


class _AccessSession:
    def __init__(self, project=None, participates=False):
        self.project = project
        self.participates = participates

    def get(self, _model, _key):
        return self.project

    def query(self, *_args):
        return _ParticipationQuery(self.participates)


def test_shift_comment_access_uses_owner_and_specification_leader_even_when_signed():
    service = ReportCommentService()
    owner_id, other_id, leader_id = uuid4(), uuid4(), uuid4()
    report = SimpleNamespace(user=owner_id, project=uuid4(), signed=True)
    own_actor = CommentActor(owner_id, "user")
    assert service._allowed(_AccessSession(), "shift", report, own_actor, create=True)
    assert not service._allowed(_AccessSession(), "shift", report, CommentActor(other_id, "user"), create=True)
    leader_session = _AccessSession(project=SimpleNamespace(project_leader=leader_id))
    assert service._allowed(leader_session, "shift", report, CommentActor(leader_id, "project-leader"), create=True)


def test_acceptance_executor_access_requires_participation_in_accepted_work():
    service = ReportCommentService()
    user_id = uuid4()
    acceptance = SimpleNamespace(id=uuid4(), project_id=uuid4())
    actor = CommentActor(user_id, "user")
    project = SimpleNamespace(project_leader=uuid4(), project_id=acceptance.project_id)
    assert service._can_view_acceptance(_AccessSession(project, participates=True), acceptance, actor)
    assert not service._can_view_acceptance(_AccessSession(project, participates=False), acceptance, actor)


def test_comment_attachments_follow_author_and_five_minute_edit_rules():
    author_id, other_id = uuid4(), uuid4()
    created_at = 1_800_000_000_000
    ensure_comment_attachment_mutable(
        author_id, created_at, CommentActor(author_id, "user"), created_at + 300_000
    )
    with pytest.raises(CommentError, match="Only the comment author"):
        ensure_comment_attachment_mutable(
            author_id, created_at, CommentActor(other_id, "manager"), created_at
        )
    with pytest.raises(CommentError, match="window of five minutes"):
        ensure_comment_attachment_mutable(
            author_id, created_at, CommentActor(author_id, "user"), created_at + 300_001
        )


def test_comment_delete_removes_attachment_rows_and_deletes_s3_after_commit(monkeypatch):
    comment_id, attachment_id = uuid4(), uuid4()
    comment = SimpleNamespace(shift_report_comment_id=comment_id, created_by=uuid4())
    attachment = SimpleNamespace(attachment_id=attachment_id)

    class Query:
        def filter(self, *_args):
            return self

        def delete(self, synchronize_session=False):
            assert synchronize_session is False

    class Session:
        committed = False
        deleted = []

        def get(self, model, _key):
            if model is report_comment_service.ShiftReportComments:
                return comment
            if model is report_comment_service.Attachments:
                return attachment
            return None

        def query(self, _model):
            return Query()

        def delete(self, item):
            self.deleted.append(item)

        def commit(self):
            self.committed = True

        def rollback(self):
            raise AssertionError("Unexpected rollback")

        def close(self):
            pass

    session = Session()
    monkeypatch.setattr(report_comment_service, "comment_attachment_cleanup", lambda *_args, **_kwargs: CommentAttachmentCleanup((attachment_id,), ("s3/key",)))
    monkeypatch.setattr(report_comment_service, "delete_s3_objects", lambda keys: (assert_s3_after_commit(session, keys)))
    monkeypatch.setattr(report_comment_service.ReportCommentService, "_session", lambda _self: session)

    report_comment_service.ReportCommentService().delete(
        "shift", comment_id, CommentActor(comment.created_by, "admin")
    )
    assert session.committed
    assert comment in session.deleted
    assert attachment in session.deleted


def assert_s3_after_commit(session, keys):
    assert session.committed
    assert keys == ("s3/key",)


@pytest.mark.parametrize("kind", ["acceptance", "shift"])
def test_parent_hard_delete_cleans_comment_attachments(monkeypatch, kind):
    parent_id = uuid4()
    cleanup = CommentAttachmentCleanup((uuid4(),), ("s3/parent-key",))

    class Manager:
        def get_project_id(self, _parent_id):
            return uuid4()

        def delete(self, _parent_id):
            return object()

    class Session:
        def close(self):
            pass

    class SessionFactory:
        def __call__(self):
            return Session()

        def remove(self):
            pass

    manager = Manager()
    cleaned = []

    if kind == "acceptance":
        module = acceptance_repository_module
        repo = module.SQLAlchemyAcceptanceRepository(manager=cast(AcceptancesManager, manager))
        monkeypatch.setattr(module.db_globals, "Session", SessionFactory())
        monkeypatch.setattr(module, "comment_attachment_cleanup", lambda *_args, **_kwargs: cleanup)
        monkeypatch.setattr(module, "cleanup_after_parent_delete", cleaned.append)
        assert repo.delete_acceptance(parent_id)
    else:
        module = shift_repository_module
        repo = module.SQLAlchemyShiftReportRepository(reports_manager=cast(ShiftReportsManager, manager))
        monkeypatch.setattr(module.db_globals, "Session", SessionFactory())
        monkeypatch.setattr(module.SQLAlchemyShiftReportRepository, "get_shift_report", lambda *_args: SimpleNamespace(project=uuid4()))
        monkeypatch.setattr(module, "comment_attachment_cleanup", lambda *_args, **_kwargs: cleanup)
        monkeypatch.setattr(module, "cleanup_after_parent_delete", cleaned.append)
        assert repo.delete_shift_report(parent_id)

    assert cleaned == [cleanup]
