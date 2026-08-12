from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import app.database.models  # noqa: F401
from flask import Flask
from flask_restx import Api

from app.database.db_setup import Base
from app.web.attachments import (
    object_attachment_ns,
    project_attachment_ns,
    shift_report_attachment_ns,
)
from app.web.attachments.contract import attachment_view_model

MIGRATION_PATH = (
    Path(__file__).parents[1] / "alembic/versions/20260811_attachments.py"
)


def test_attachment_tables_follow_project_identifier_contract():
    assert set(Base.metadata.tables).issuperset(
        {
            "attachments",
            "project_attachments",
            "shift_report_attachments",
            "object_attachments",
        }
    )
    assert "attachment_id" in Base.metadata.tables["attachments"].c
    assert "project_attachment_id" in Base.metadata.tables["project_attachments"].c
    assert "shift_report_attachment_id" in Base.metadata.tables[
        "shift_report_attachments"
    ].c
    assert "object_attachment_id" in Base.metadata.tables["object_attachments"].c
    assert "company_id" not in Base.metadata.tables["attachments"].c


def test_attachment_migration_follows_current_head_and_defines_all_permissions():
    spec = spec_from_file_location("attachments_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.down_revision == "20260811_place_rel_perms"
    assert len(migration.PERMISSIONS) == 12
    assert (
        "projects-attachments-upload",
        "POST /projects/{project_id}/attachments",
    ) in migration.PERMISSIONS


def test_attachment_swagger_contract_exposes_all_target_routes():
    app = Flask(__name__)
    api = Api(app)
    for namespace in (
        project_attachment_ns,
        shift_report_attachment_ns,
        object_attachment_ns,
    ):
        api.add_namespace(namespace)

    response = app.test_client().get("/swagger.json")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert set(payload["paths"]) == {
        f"/{target}/{{{target_id}}}/attachments{suffix}"
        for target, target_id in (
            ("projects", "project_id"),
            ("shift_reports", "shift_report_id"),
            ("objects", "object_id"),
        )
        for suffix in ("", "/{attachment_id}", "/{attachment_id}/download")
    }

    upload_contract = payload["paths"][
        "/shift_reports/{shift_report_id}/attachments"
    ]["post"]
    assert upload_contract["consumes"] == ["multipart/form-data"]
    assert upload_contract["parameters"][0]["type"] == "file"


def test_attachment_view_contract_excludes_preview_url():
    assert "download_url" not in attachment_view_model
