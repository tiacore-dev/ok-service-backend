from uuid import uuid4, UUID
from sqlalchemy.orm import aliased
from sqlalchemy.sql import func
from sqlalchemy.exc import SQLAlchemyError
from app.database.models import ShiftReports, ShiftReportDetails
from app.database.managers.abstract_manager import BaseDBManager


class ShiftReportsManager(BaseDBManager):

    @property
    def model(self):
        return ShiftReports

    def get_total_sum_by_shift_report(self, shift_report_id):
        """Возвращает сумму всех `summ` из shift_report_details для shift_report_id"""
        with self.session_scope() as session:

            # Создаем алиасы для удобства
            sr = aliased(ShiftReports)
            srd = aliased(ShiftReportDetails)

            result = (
                session.query(func.sum(srd.summ))
                .select_from(sr)  # Явно указываем, с какой таблицы начинаем
                # Указываем ON-условие
                .join(srd, sr.shift_report_id == srd.shift_report)
                .filter(sr.shift_report_id == shift_report_id)
                .scalar()
            )

            return result or 0  # Если записей нет, возвращаем 0

    def add_shift_report_with_details(self, data):
        """Добавляет shift_report и shift_report_details в одной транзакции"""

        shift_report_data = {
            "shift_report_id": uuid4(),
            "user": UUID(data['user']),
            "date": data['date'],
            "project": UUID(data['project']),
            "signed": data.get("signed", False),  # По умолчанию False
        }

        shift_report_details_data = data.get(
            "details", [])  # Детали могут отсутствовать

        with self.session_scope() as session:
            try:
                # 1. Создаем `shift_report`
                new_report = ShiftReports(**shift_report_data)
                session.add(new_report)
                session.flush()  # Генерирует shift_report_id без коммита

                # 2. Создаем `shift_report_details`, если есть
                if shift_report_details_data:
                    details = [
                        ShiftReportDetails(
                            shift_report=new_report.shift_report_id,
                            work=UUID(detail['work']),
                            quantity=detail['quantity'],
                            summ=detail['summ']
                        ) for detail in shift_report_details_data
                    ]

                    # Массовая вставка `shift_report_details`
                    session.add_all(details)

                session.commit()  # Сохраняем все одной транзакцией

                return new_report.to_dict()  # Возвращаем ID созданного отчета

            except SQLAlchemyError as e:
                session.rollback()
                raise e  # Выбрасываем исключение выше, чтобы обработать в API


class ShiftReportsDetailsManager(BaseDBManager):

    @property
    def model(self):
        return ShiftReportDetails
