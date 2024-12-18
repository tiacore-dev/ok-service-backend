from app.database.models import ShiftReports, ShiftReportDetails
# Предполагается, что BaseDBManager в другом файле
from app.database.managers.abstract_manager import BaseDBManager


class ShiftReportsManager(BaseDBManager):

    @property
    def model(self):
        return ShiftReports


class ShiftReportsDetailsManager(BaseDBManager):

    @property
    def model(self):
        return ShiftReportDetails
