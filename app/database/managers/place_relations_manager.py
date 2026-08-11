from app.database.managers.abstract_manager import BaseDBManager
from app.database.models import ProjectPlaceRelations, ShiftPlaceRelations


class ProjectPlaceRelationsManager(BaseDBManager):
    @property
    def model(self):
        return ProjectPlaceRelations


class ShiftPlaceRelationsManager(BaseDBManager):
    @property
    def model(self):
        return ShiftPlaceRelations
