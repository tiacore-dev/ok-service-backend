from flask_restx import Api

from .leaves.routes import leave_ns
from .project_materials.routes import project_material_ns
from .work_prices.routes import work_price_ns


def register_namespaces(api: Api):
    api.add_namespace(leave_ns)
    api.add_namespace(project_material_ns)
    api.add_namespace(work_price_ns)
