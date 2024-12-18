from app.database.models import Works, WorkPrices, WorkCategories
# Предполагается, что BaseDBManager в другом файле
from app.database.managers.abstract_manager import BaseDBManager


class WorksManager(BaseDBManager):

    @property
    def model(self):
        return Works


class WorksPricessManager(BaseDBManager):

    @property
    def model(self):
        return WorkPrices


class WorksCategoriesManager(BaseDBManager):

    @property
    def model(self):
        return WorkCategories
