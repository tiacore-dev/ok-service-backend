from flask import Flask

from app.decorators.role_decorators import admin_manager_or_project_leader_required


def test_project_leader_is_allowed_without_project_scope_check(monkeypatch):
    app = Flask(__name__)
    monkeypatch.setattr(
        "app.decorators.role_decorators.get_jwt_identity",
        lambda: {"role": "project-leader", "user_id": "user-id"},
    )

    @admin_manager_or_project_leader_required
    def protected():
        return {"msg": "ok"}, 200

    with app.test_request_context():
        assert protected() == ({"msg": "ok"}, 200)


def test_regular_user_is_forbidden(monkeypatch):
    app = Flask(__name__)
    monkeypatch.setattr(
        "app.decorators.role_decorators.get_jwt_identity",
        lambda: {"role": "user", "user_id": "user-id"},
    )

    @admin_manager_or_project_leader_required
    def protected():
        return {"msg": "ok"}, 200

    with app.test_request_context():
        assert protected() == ({"msg": "Forbidden"}, 403)
