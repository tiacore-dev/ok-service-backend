from app.database.models import Objects, ObjectStatuses
from app.database.managers.abstract_manager import BaseDBManager  # Предполагается, что BaseDBManager в другом файле


class ObjectsManager(BaseDBManager):

    @property
    def model(self):
        return Objects


class ObjectStatusesManager(BaseDBManager):

    @property
    def model(self):
        return ObjectStatuses