from flask import Flask
from flask_restx import Api

from app.web import register_namespaces as register_web_namespaces

from .account_route import account_bp
from .namespaces.login_ns import login_ns
from .namespaces.role_ns import role_ns
from .namespaces.subscrtiption_ns import subscription_ns


def register_routes(app: Flask):
    app.register_blueprint(account_bp)
    # app.register_blueprint(push_bp)


def register_namespaces(api: Api):
    api.add_namespace(login_ns)
    api.add_namespace(role_ns)
    api.add_namespace(subscription_ns)
    register_web_namespaces(api)
