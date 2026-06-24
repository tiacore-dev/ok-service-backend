from app.database.models import Positions
from app.database.managers.abstract_manager import BaseDBManager


class PositionsManager(BaseDBManager):

    @property
    def model(self):
        return Positions
