from app.models import Roles
from app.database.managers.abstract_manager import BaseDBManager  # Предполагается, что BaseDBManager в другом файле


class RolesManager(BaseDBManager):

    @property
    def model(self):
        return Roles


