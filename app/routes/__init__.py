from flask import Flask
from flask_restx import Api

from app.web import register_namespaces as register_web_namespaces

from .account_route import account_bp


def register_routes(app: Flask):
    app.register_blueprint(account_bp)
    # app.register_blueprint(push_bp)


def register_namespaces(api: Api):
    register_web_namespaces(api)
