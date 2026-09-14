from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import app.database.models  # noqa: F401
from flask import Flask
from flask_restx import Api

from app.database.db_setup import Base
from app.web.attachments import (
    acceptance_attachment_ns,
    object_attachment_ns,
    place_attachment_ns,
    project_attachment_ns,
    shift_report_attachment_ns,
)
from app.web.attachments.contract import attachment_view_model
from app.web.acceptances import acceptance_ns

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
            "place_attachments",
            "work_acceptance_attachments",
        }
    )
    assert "attachment_id" in Base.metadata.tables["attachments"].c
    assert "project_attachment_id" in Base.metadata.tables["project_attachments"].c
    assert "shift_report_attachment_id" in Base.metadata.tables[
        "shift_report_attachments"
    ].c
    assert "object_attachment_id" in Base.metadata.tables["object_attachments"].c
    assert "place_attachment_id" in Base.metadata.tables["place_attachments"].c
    assert "work_acceptance_attachment_id" in Base.metadata.tables[
        "work_acceptance_attachments"
    ].c
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
        place_attachment_ns,
        acceptance_attachment_ns,
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
            ("places", "place_id"),
            ("acceptances", "acceptance_id"),
        )
        for suffix in ("", "/{attachment_id}", "/{attachment_id}/download")
    }

    upload_contract = payload["paths"][
        "/shift_reports/{shift_report_id}/attachments"
    ]["post"]
    assert upload_contract["consumes"] == ["multipart/form-data"]
    assert upload_contract["parameters"][0]["type"] == "file"


def test_place_attachment_migration_declares_relation_and_permissions():
    migration_path = (
        Path(__file__).parents[1] / "alembic/versions/20260818_place_attachments.py"
    )
    spec = spec_from_file_location("place_attachments_migration", migration_path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.revision == "20260818_place_attach"
    assert migration.down_revision == "20260811_attachments"
    assert len(migration.PERMISSIONS) == 4
    assert (
        "places-attachments-upload",
        "POST /places/{place_id}/attachments",
    ) in migration.PERMISSIONS


def test_work_acceptance_attachment_migration_declares_relation_and_permissions():
    migration_path = (
        Path(__file__).parents[1]
        / "alembic/versions/20260903090000_work_acceptance_attachments.py"
    )
    spec = spec_from_file_location("work_acceptance_attachments_migration", migration_path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.down_revision == "20260831130000"
    assert len(migration.PERMISSIONS) == 4
    assert "key_permission_type_relations" not in migration_path.read_text()
    assert (
        "acceptances-attachments-upload",
        "POST /acceptances/{acceptance_id}/attachments",
    ) in migration.PERMISSIONS


def test_attachment_view_contract_excludes_preview_url():
    assert "download_url" not in attachment_view_model


def test_acceptance_detail_model_is_registered_for_swagger():
    assert "AcceptanceView" in acceptance_ns.models
