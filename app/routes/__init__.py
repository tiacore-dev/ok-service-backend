from flask import Flask
from flask_restx import Api
from .account_route import account_bp
from .namespaces.login_ns import login_ns
from .namespaces.user_ns import user_ns
from .namespaces.object_status_ns import object_status_ns
from .namespaces.work_category_ns import work_category_ns
from .namespaces.object_ns import object_ns


def register_routes(app: Flask):
    app.register_blueprint(account_bp)


def register_namespaces(api: Api):
    api.add_namespace(login_ns)
    api.add_namespace(user_ns)
    api.add_namespace(object_status_ns)
    api.add_namespace(work_category_ns)
    api.add_namespace(object_ns)
