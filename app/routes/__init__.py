from flask import Flask
from flask_restx import Api
from .account_route import account_bp
# from .push_route import push_bp
from .namespaces.login_ns import login_ns
from .namespaces.user_ns import user_ns
from .namespaces.object_status_ns import object_status_ns
from .namespaces.work_category_ns import work_category_ns
from .namespaces.object_ns import object_ns
from .namespaces.project_ns import project_ns
from .namespaces.work_ns import work_ns
from .namespaces.work_price_ns import work_price_ns
from .namespaces.project_work_ns import project_work_ns
from .namespaces.project_schedule_ns import project_schedule_ns
from .namespaces.shift_report_ns import shift_report_ns
from .namespaces.role_ns import role_ns
from .namespaces.shift_report_detail_ns import shift_report_details_ns
from .namespaces.subscrtiption_ns import subscription_ns


def register_routes(app: Flask):
    app.register_blueprint(account_bp)
    # app.register_blueprint(push_bp)


def register_namespaces(api: Api):
    api.add_namespace(login_ns)
    api.add_namespace(user_ns)
    api.add_namespace(object_status_ns)
    api.add_namespace(work_category_ns)
    api.add_namespace(object_ns)
    api.add_namespace(project_ns)
    api.add_namespace(work_ns)
    api.add_namespace(work_price_ns)
    api.add_namespace(project_work_ns)
    api.add_namespace(project_schedule_ns)
    api.add_namespace(shift_report_ns)
    api.add_namespace(role_ns)
    api.add_namespace(shift_report_details_ns)
    api.add_namespace(subscription_ns)
