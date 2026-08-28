import logging

from app.database.managers.abstract_manager import BaseDBManager
from app.database.models import (
    Materials,
    ProjectMaterials,
    ShiftReportMaterials,
    WorkMaterialRelations,
    Acceptances,
    WorkAcceptanceRelations,
)

logger = logging.getLogger("ok_service")


class MaterialsManager(BaseDBManager):
    @property
    def model(self):
        return Materials


class WorkMaterialRelationsManager(BaseDBManager):
    @property
    def model(self):
        return WorkMaterialRelations


class ProjectMaterialsManager(BaseDBManager):
    @property
    def model(self):
        return ProjectMaterials


class ShiftReportMaterialsManager(BaseDBManager):
    @property
    def model(self):
        return ShiftReportMaterials


class AcceptancesManager(BaseDBManager):
    @property
    def model(self):
        return Acceptances


class WorkAcceptanceRelationsManager(BaseDBManager):
    @property
    def model(self):
        return WorkAcceptanceRelations
