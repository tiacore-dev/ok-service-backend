from flask_restx import Api

from .api_keys.routes import api_key_ns
from .auth.routes import login_ns
from .attachments import (
    object_attachment_ns,
    place_attachment_ns,
    project_attachment_ns,
    shift_report_attachment_ns,
)
from .cities.routes import city_ns
from .leaves.routes import leave_ns
from .materials.routes import material_ns
from .measurement_units.routes import measurement_unit_ns
from .object_statuses.routes import object_status_ns
from .objects.routes import object_ns
from .places.routes import place_ns
from .place_relations.routes import project_place_relation_ns, shift_place_relation_ns
from .positions.routes import position_ns
from .project_materials.routes import project_material_ns
from .project_schedules.routes import project_schedule_ns
from .project_works.routes import project_work_ns
from .work_plans import work_plan_ns
from .projects.routes import project_ns
from .roles.routes import role_ns
from .shift_report_materials.routes import shift_report_material_ns
from .shift_reports.routes import shift_report_details_ns, shift_report_ns
from .subscriptions.routes import subscription_ns
from .template_generation.routes import template_ns
from .users.routes import user_ns
from .work_categories.routes import work_category_ns
from .work_material_relations.routes import work_material_relation_ns
from .acceptances.routes import acceptance_ns
from .work_acceptance_relations.routes import work_acceptance_relation_ns
from .work_prices.routes import work_price_ns
from .works.routes import work_ns


def register_namespaces(api: Api):
    api.add_namespace(login_ns)
    api.add_namespace(project_attachment_ns)
    api.add_namespace(shift_report_attachment_ns)
    api.add_namespace(object_attachment_ns)
    api.add_namespace(place_attachment_ns)
    api.add_namespace(role_ns)
    api.add_namespace(subscription_ns)
    api.add_namespace(api_key_ns)
    api.add_namespace(leave_ns)
    api.add_namespace(city_ns)
    api.add_namespace(object_ns)
    api.add_namespace(place_ns)
    api.add_namespace(project_place_relation_ns)
    api.add_namespace(shift_place_relation_ns)
    api.add_namespace(object_status_ns)
    api.add_namespace(position_ns)
    api.add_namespace(project_schedule_ns)
    api.add_namespace(project_ns)
    api.add_namespace(user_ns)
    api.add_namespace(shift_report_ns)
    api.add_namespace(shift_report_details_ns)
    api.add_namespace(project_material_ns)
    api.add_namespace(material_ns)
    api.add_namespace(measurement_unit_ns)
    api.add_namespace(project_work_ns)
    api.add_namespace(work_plan_ns)
    api.add_namespace(work_category_ns)
    api.add_namespace(work_material_relation_ns)
    api.add_namespace(acceptance_ns)
    api.add_namespace(work_acceptance_relation_ns)
    api.add_namespace(shift_report_material_ns)
    api.add_namespace(work_price_ns)
    api.add_namespace(work_ns)
    api.add_namespace(template_ns)
