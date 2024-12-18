from app.database.models import Roles
# Предполагается, что BaseDBManager в другом файле
from app.database.managers.abstract_manager import BaseDBManager


class RolesManager(BaseDBManager):

    @property
    def model(self):
        return Roles
