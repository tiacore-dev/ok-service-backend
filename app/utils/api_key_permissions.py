"""Canonical API-key permission seed and idempotent bootstrap."""

from app.database import db_globals
from app.database.models import PermissionTypes

# Keep this list in sync with endpoints decorated by
# ``api_key_or_jwt_required``.  The description is part of the authorization
# contract: the decorator resolves the permission by HTTP method and route.
API_KEY_PERMISSIONS = (
    ("places-add", "POST /places/add"),
    ("places-delete-hard", "DELETE /places/{place_id}/delete/hard"),
    ("places-delete-soft", "PATCH /places/{place_id}/delete/soft"),
    ("places-edit", "PATCH /places/{place_id}/edit"),
    ("places-list", "GET /places/all"),
    ("places-view", "GET /places/{place_id}/view"),
    ("cities-create", "POST /cities/add"),
    ("cities-delete-hard", "DELETE /cities/{city_id}/delete/hard"),
    ("cities-delete-soft", "PATCH /cities/{city_id}/delete/soft"),
    ("cities-edit", "PATCH /cities/{city_id}/edit"),
    ("cities-list", "GET /cities/all"),
    ("cities-view", "GET /cities/{city_id}/view"),
    ("leaves-create", "POST /leaves/add"),
    ("leaves-delete-hard", "DELETE /leaves/{leave_id}/delete/hard"),
    ("leaves-delete-soft", "PATCH /leaves/{leave_id}/delete/soft"),
    ("leaves-edit", "PATCH /leaves/{leave_id}/edit"),
    ("leaves-list", "GET /leaves/all"),
    ("leaves-reasons-list", "GET /leaves/reasons/all"),
    ("leaves-view", "GET /leaves/{leave_id}/view"),
    ("materials-create", "POST /materials/add"),
    ("materials-delete-hard", "DELETE /materials/{material_id}/delete/hard"),
    ("materials-delete-soft", "PATCH /materials/{material_id}/delete/soft"),
    ("materials-edit", "PATCH /materials/{material_id}/edit"),
    ("materials-list", "GET /materials/all"),
    ("materials-view", "GET /materials/{material_id}/view"),
    (
        "objects-attachments-delete",
        "DELETE /objects/{object_id}/attachments/{attachment_id}",
    ),
    (
        "objects-attachments-download",
        "GET /objects/{object_id}/attachments/{attachment_id}/download",
    ),
    ("objects-attachments-list", "GET /objects/{object_id}/attachments"),
    ("objects-attachments-upload", "POST /objects/{object_id}/attachments"),
    ("objects-create", "POST /objects/add"),
    ("objects-delete-hard", "DELETE /objects/{object_id}/delete/hard"),
    ("objects-delete-soft", "PATCH /objects/{object_id}/delete/soft"),
    ("objects-edit", "PATCH /objects/{object_id}/edit"),
    ("objects-list", "GET /objects/all"),
    ("object-statuses-list", "GET /object_statuses/all"),
    ("objects-view", "GET /objects/{object_id}/view"),
    (
        "places-attachments-delete",
        "DELETE /places/{place_id}/attachments/{attachment_id}",
    ),
    (
        "places-attachments-download",
        "GET /places/{place_id}/attachments/{attachment_id}/download",
    ),
    ("places-attachments-list", "GET /places/{place_id}/attachments"),
    ("places-attachments-upload", "POST /places/{place_id}/attachments"),
    ("positions-create", "POST /positions/add"),
    ("positions-delete-hard", "DELETE /positions/{position_id}/delete/hard"),
    ("positions-edit", "PATCH /positions/{position_id}/edit"),
    ("positions-list", "GET /positions/all"),
    ("positions-view", "GET /positions/{position_id}/view"),
    ("project-materials-create", "POST /project_materials/add"),
    (
        "project-materials-delete-hard",
        "DELETE /project_materials/{project_material_id}/delete/hard",
    ),
    ("project-materials-edit", "PATCH /project_materials/{project_material_id}/edit"),
    ("project-materials-list", "GET /project_materials/all"),
    ("project-materials-view", "GET /project_materials/{project_material_id}/view"),
    ("project-place-relations-add", "POST /project_place_relations/add"),
    ("project-place-relations-add-bulk", "POST /project_place_relations/add-bulk"),
    (
        "project-place-relations-delete",
        "DELETE /project_place_relations/{relation_id}/delete/hard",
    ),
    (
        "project-place-relations-delete-bulk",
        "DELETE /project_place_relations/delete-bulk",
    ),
    (
        "project-place-relations-edit",
        "PATCH /project_place_relations/{relation_id}/edit",
    ),
    ("project-place-relations-list", "GET /project_place_relations/all"),
    ("project-place-relations-view", "GET /project_place_relations/{relation_id}/view"),
    (
        "projects-attachments-delete",
        "DELETE /projects/{project_id}/attachments/{attachment_id}",
    ),
    (
        "projects-attachments-download",
        "GET /projects/{project_id}/attachments/{attachment_id}/download",
    ),
    ("projects-attachments-list", "GET /projects/{project_id}/attachments"),
    ("projects-attachments-upload", "POST /projects/{project_id}/attachments"),
    ("project-schedules-create", "POST /project_schedules/add"),
    (
        "project-schedules-delete-hard",
        "DELETE /project_schedules/{schedule_id}/delete/hard",
    ),
    ("project-schedules-edit", "PATCH /project_schedules/{schedule_id}/edit"),
    ("project-schedules-list", "GET /project_schedules/all"),
    ("project-schedules-view", "GET /project_schedules/{schedule_id}/view"),
    ("projects-create", "POST /projects/add"),
    ("projects-delete-hard", "DELETE /projects/{project_id}/delete/hard"),
    ("projects-delete-soft", "PATCH /projects/{project_id}/delete/soft"),
    ("projects-edit", "PATCH /projects/{project_id}/edit"),
    ("projects-get-stat", "GET /projects/{project_id}/get-stat"),
    ("objects-get-stat", "GET /objects/{object_id}/get-stat"),
    ("objects-get-stat-details", "GET /objects/{object_id}/get-stat-details"),
    ("project-leaders-get-stat", "GET /project-leaders/{project_leader_id}/get-stat"),
    ("project-leaders-get-stat-details", "GET /project-leaders/{project_leader_id}/get-stat-details"),
    (
        "projects-get-stat-by-project-materials",
        "GET /projects/{project_id}/get-stat-by-project-materials",
    ),
    ("projects-list", "GET /projects/all"),
    ("projects-view", "GET /projects/{project_id}/view"),
    ("project-works-create", "POST /project_works/add"),
    ("project-works-create-many", "POST /project_works/add/many"),
    (
        "project-works-delete-hard",
        "DELETE /project_works/{project_work_id}/delete/hard",
    ),
    ("project-works-delete-soft", "PATCH /project_works/{project_work_id}/delete/soft"),
    ("project-works-edit", "PATCH /project_works/{project_work_id}/edit"),
    ("project-works-list", "GET /project_works/all"),
    ("project-works-view", "GET /project_works/{project_work_id}/view"),
    ("roles-list", "GET /roles/all"),
    ("shift-place-relations-add", "POST /shift_place_relations/add"),
    ("shift-place-relations-add-bulk", "POST /shift_place_relations/add-bulk"),
    (
        "shift-place-relations-delete",
        "DELETE /shift_place_relations/{relation_id}/delete/hard",
    ),
    ("shift-place-relations-delete-bulk", "DELETE /shift_place_relations/delete-bulk"),
    ("shift-place-relations-edit", "PATCH /shift_place_relations/{relation_id}/edit"),
    ("shift-place-relations-list", "GET /shift_place_relations/all"),
    ("shift-place-relations-view", "GET /shift_place_relations/{relation_id}/view"),
    (
        "shift-report-details-all-by-reports",
        "POST /shift_report_details/all-by-reports",
    ),
    ("shift-report-details-create", "POST /shift_report_details/add"),
    ("shift-report-details-create-many", "POST /shift_report_details/add/many"),
    (
        "shift-report-details-delete-hard",
        "DELETE /shift_report_details/{detail_id}/delete/hard",
    ),
    ("shift-report-details-edit", "PATCH /shift_report_details/{detail_id}/edit"),
    ("shift-report-details-list", "GET /shift_report_details/all"),
    ("shift-report-details-view", "GET /shift_report_details/{detail_id}/view"),
    ("shift-report-materials-create", "POST /shift_report_materials/add"),
    (
        "shift-report-materials-delete-hard",
        "DELETE /shift_report_materials/{shift_report_material_id}/delete/hard",
    ),
    (
        "shift-report-materials-edit",
        "PATCH /shift_report_materials/{shift_report_material_id}/edit",
    ),
    ("shift-report-materials-list", "GET /shift_report_materials/all"),
    (
        "shift-report-materials-view",
        "GET /shift_report_materials/{shift_report_material_id}/view",
    ),
    (
        "shift_reports-attachments-delete",
        "DELETE /shift_reports/{shift_report_id}/attachments/{attachment_id}",
    ),
    (
        "shift_reports-attachments-download",
        "GET /shift_reports/{shift_report_id}/attachments/{attachment_id}/download",
    ),
    (
        "shift_reports-attachments-list",
        "GET /shift_reports/{shift_report_id}/attachments",
    ),
    (
        "shift_reports-attachments-upload",
        "POST /shift_reports/{shift_report_id}/attachments",
    ),
    ("shift-reports-create", "POST /shift_reports/add"),
    ("shift-reports-delete-hard", "DELETE /shift_reports/{report_id}/delete/hard"),
    ("shift-reports-delete-soft", "PATCH /shift_reports/{report_id}/delete/soft"),
    ("shift-reports-edit", "PATCH /shift_reports/{report_id}/edit"),
    ("shift-reports-finish", "PATCH /shift_reports/{report_id}/finish"),
    ("shift-reports-list", "GET /shift_reports/all"),
    ("shift-reports-sign", "PATCH /shift_reports/{report_id}/sign"),
    ("shift-reports-start", "PATCH /shift_reports/{report_id}/start"),
    ("shift-reports-view", "GET /shift_reports/{report_id}/view"),
    ("users-create", "POST /users/add"),
    ("users-delete-hard", "DELETE /users/{user_id}/delete/hard"),
    ("users-delete-soft", "PATCH /users/{user_id}/delete/soft"),
    ("users-edit", "PATCH /users/{user_id}/edit"),
    ("users-list", "GET /users/all"),
    ("users-restore", "PATCH /users/{user_id}/restore"),
    ("users-view", "GET /users/{user_id}/view"),
    ("work-categories-create", "POST /work_categories/add"),
    (
        "work-categories-delete-hard",
        "DELETE /work_categories/{work_category_id}/delete/hard",
    ),
    (
        "work-categories-delete-soft",
        "PATCH /work_categories/{work_category_id}/delete/soft",
    ),
    ("work-categories-edit", "PATCH /work_categories/{work_category_id}/edit"),
    ("work-categories-list", "GET /work_categories/all"),
    ("work-categories-view", "GET /work_categories/{work_category_id}/view"),
    ("work-material-relations-create", "POST /work_material_relations/add"),
    (
        "work-material-relations-delete-hard",
        "DELETE /work_material_relations/{relation_id}/delete/hard",
    ),
    (
        "work-material-relations-edit",
        "PATCH /work_material_relations/{relation_id}/edit",
    ),
    ("work-material-relations-list", "GET /work_material_relations/all"),
    ("work-material-relations-view", "GET /work_material_relations/{relation_id}/view"),
    ("work-prices-create", "POST /work_prices/add"),
    ("work-prices-delete-hard", "DELETE /work_prices/{work_price_id}/delete/hard"),
    ("work-prices-delete-soft", "PATCH /work_prices/{work_price_id}/delete/soft"),
    ("work-prices-edit", "PATCH /work_prices/{work_price_id}/edit"),
    ("work-prices-list", "GET /work_prices/all"),
    ("work-prices-view", "GET /work_prices/{work_price_id}/view"),
    ("works-create", "POST /works/add"),
    ("works-delete-hard", "DELETE /works/{work_id}/delete/hard"),
    ("works-delete-soft", "PATCH /works/{work_id}/delete/soft"),
    ("works-edit", "PATCH /works/{work_id}/edit"),
    ("works-list", "GET /works/all"),
    ("works-view", "GET /works/{work_id}/view"),
    ("measurement-units-create", "POST /measurement_units/add"),
    (
        "measurement-units-delete-hard",
        "DELETE /measurement_units/{measurement_unit_id}/delete/hard",
    ),
    ("measurement-units-edit", "PATCH /measurement_units/{measurement_unit_id}/edit"),
    ("measurement-units-list", "GET /measurement_units/all"),
    ("measurement-units-view", "GET /measurement_units/{measurement_unit_id}/view"),
    ("acceptances-create", "POST /acceptances/add"),
    ("acceptances-delete-hard", "DELETE /acceptances/{acceptance_id}/delete/hard"),
    ("acceptances-edit", "PATCH /acceptances/{acceptance_id}/edit"),
    ("acceptances-history-list", "GET /acceptances/{acceptance_id}/history"),
    ("acceptances-list", "GET /acceptances/all"),
    ("acceptances-view", "GET /acceptances/{acceptance_id}/view"),
    ("work-acceptance-relations-create", "POST /work-acceptance-relations/add"),
    (
        "work-acceptance-relations-delete-hard",
        "DELETE /work-acceptance-relations/{relation_id}/delete/hard",
    ),
    (
        "work-acceptance-relations-edit",
        "PATCH /work-acceptance-relations/{relation_id}/edit",
    ),
    ("work-acceptance-relations-list", "GET /work-acceptance-relations/all"),
    (
        "work-acceptance-relations-view",
        "GET /work-acceptance-relations/{relation_id}/view",
    ),
    ("work-plans-create", "POST /work_plans/add"),
    ("work-plans-delete-hard", "DELETE /work_plans/{work_plan_id}/delete/hard"),
    ("work-plans-delete-soft", "PATCH /work_plans/{work_plan_id}/delete/soft"),
    ("work-plans-edit", "PATCH /work_plans/{work_plan_id}/edit"),
    ("work-plans-list", "GET /work_plans/all"),
    ("work-plans-view", "GET /work_plans/{work_plan_id}/view"),
)


def set_api_key_permissions() -> int:
    """Insert missing API-key permissions and return the number inserted."""
    session_factory = db_globals.Session
    if session_factory is None:
        raise RuntimeError("Database session is not initialized")

    session = session_factory()
    try:
        codes = {code for code, _ in API_KEY_PERMISSIONS}
        existing_codes = {
            code
            for (code,) in session.query(PermissionTypes.code)
            .filter(PermissionTypes.code.in_(codes))
            .all()
        }
        missing = [
            PermissionTypes(code=code, description=description)
            for code, description in API_KEY_PERMISSIONS
            if code not in existing_codes
        ]
        if missing:
            session.add_all(missing)
            session.commit()
        else:
            session.rollback()
        return len(missing)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
