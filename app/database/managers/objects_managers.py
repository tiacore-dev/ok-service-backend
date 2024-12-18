from app.database.models import Objects, ObjectStatuses
# Предполагается, что BaseDBManager в другом файле
from app.database.managers.abstract_manager import BaseDBManager


class ObjectsManager(BaseDBManager):

    @property
    def model(self):
        return Objects


class ObjectStatusesManager(BaseDBManager):

    @property
    def model(self):
        return ObjectStatuses
