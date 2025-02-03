from sqlalchemy.orm import aliased
from sqlalchemy.sql import func
from app.database.models import ShiftReports, ShiftReportDetails
# Предполагается, что BaseDBManager в другом файле
from app.database.managers.abstract_manager import BaseDBManager


class ShiftReportsManager(BaseDBManager):

    @property
    def model(self):
        return ShiftReports

    def get_total_sum_by_shift_report(self, shift_report_id):
        """Возвращает сумму всех `summ` из shift_report_details для shift_report_id"""
        with self.session_scope() as session:  # Предполагаем, что session есть в `BaseDBManager`

            # Алайс для удобства
            sr = aliased(ShiftReports)
            srd = aliased(ShiftReportDetails)

            result = (
                session.query(func.sum(srd.summ))
                .join(srd, sr.shift_report_id == srd.shift_report)
                .filter(sr.shift_report_id == shift_report_id)
                .scalar()
            )

            return result or 0  # Если нет записей, возвращаем 0


class ShiftReportsDetailsManager(BaseDBManager):

    @property
    def model(self):
        return ShiftReportDetails
