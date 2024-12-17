from app.models import ShiftReports, ShiftReportDetails
from app.database.managers.abstract_manager import BaseDBManager  # Предполагается, что BaseDBManager в другом файле


class ShiftReportsManager(BaseDBManager):

    @property
    def model(self):
        return ShiftReports


class ShiftReportsDetailsManager(BaseDBManager):

    @property
    def model(self):
        return ShiftReportDetails