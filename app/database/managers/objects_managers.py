# Предполагается, что BaseDBManager в другом файле
from app.database.managers.abstract_manager import BaseDBManager
from app.database.models import Objects, ObjectStatuses, Places


class ObjectsManager(BaseDBManager):
    @property
    def model(self):
        return Objects


class ObjectStatusesManager(BaseDBManager):
    @property
    def model(self):
        return ObjectStatuses


class PlacesManager(BaseDBManager):
    @property
    def model(self):
        return Places
