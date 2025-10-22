from app.database.models import Cities
from app.database.managers.abstract_manager import BaseDBManager


class CitiesManager(BaseDBManager):

    @property
    def model(self):
        return Cities
