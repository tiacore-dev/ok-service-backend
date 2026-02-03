from flask import Flask
from flask_restx import Api

from .account_route import account_bp
from .namespaces.city_ns import city_ns
from .namespaces.leave_ns import leave_ns
from .namespaces.login_ns import login_ns
from .namespaces.material_ns import material_ns
from .namespaces.object_ns import object_ns
from .namespaces.object_status_ns import object_status_ns
from .namespaces.project_material_ns import project_material_ns
from .namespaces.project_ns import project_ns
from .namespaces.project_schedule_ns import project_schedule_ns
from .namespaces.project_work_ns import project_work_ns
from .namespaces.role_ns import role_ns
from .namespaces.shift_report_detail_ns import shift_report_details_ns
from .namespaces.shift_report_material_ns import shift_report_material_ns
from .namespaces.shift_report_ns import shift_report_ns
from .namespaces.subscrtiption_ns import subscription_ns
from .namespaces.template_ns import template_ns
from .namespaces.user_ns import user_ns
from .namespaces.work_category_ns import work_category_ns
from .namespaces.work_material_relation_ns import work_material_relation_ns
from .namespaces.work_ns import work_ns
from .namespaces.work_price_ns import work_price_ns


def register_routes(app: Flask):
    app.register_blueprint(account_bp)
    # app.register_blueprint(push_bp)


def register_namespaces(api: Api):
    api.add_namespace(login_ns)
    api.add_namespace(user_ns)
    api.add_namespace(city_ns)
    api.add_namespace(leave_ns)
    api.add_namespace(object_status_ns)
    api.add_namespace(work_category_ns)
    api.add_namespace(object_ns)
    api.add_namespace(project_ns)
    api.add_namespace(work_ns)
    api.add_namespace(work_price_ns)
    api.add_namespace(material_ns)
    api.add_namespace(work_material_relation_ns)
    api.add_namespace(project_material_ns)
    api.add_namespace(shift_report_material_ns)
    api.add_namespace(project_work_ns)
    api.add_namespace(project_schedule_ns)
    api.add_namespace(shift_report_ns)
    api.add_namespace(role_ns)
    api.add_namespace(shift_report_details_ns)
    api.add_namespace(subscription_ns)
    api.add_namespace(template_ns)
