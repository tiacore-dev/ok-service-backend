from app.database.models import Subscriptions
# Предполагается, что BaseDBManager в другом файле
from app.database.managers.abstract_manager import BaseDBManager


class SubscriptionsManager(BaseDBManager):

    @property
    def model(self):
        return Subscriptions
