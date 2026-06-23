from flask_restx import Api

from .leaves.routes import leave_ns


def register_namespaces(api: Api):
    api.add_namespace(leave_ns)
