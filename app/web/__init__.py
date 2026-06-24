from flask_restx import Api

from .leaves.routes import leave_ns
from .users.routes import user_ns
from .shift_reports.routes import shift_report_details_ns, shift_report_ns
from .project_materials.routes import project_material_ns
from .materials.routes import material_ns
from .project_works.routes import project_work_ns
from .work_categories.routes import work_category_ns
from .work_material_relations.routes import work_material_relation_ns
from .work_prices.routes import work_price_ns
from .shift_report_materials.routes import shift_report_material_ns
from .works.routes import work_ns


def register_namespaces(api: Api):
    api.add_namespace(leave_ns)
    api.add_namespace(user_ns)
    api.add_namespace(shift_report_ns)
    api.add_namespace(shift_report_details_ns)
    api.add_namespace(project_material_ns)
    api.add_namespace(material_ns)
    api.add_namespace(project_work_ns)
    api.add_namespace(work_category_ns)
    api.add_namespace(work_material_relation_ns)
    api.add_namespace(shift_report_material_ns)
    api.add_namespace(work_price_ns)
    api.add_namespace(work_ns)
