import logging

from app.database.managers.abstract_manager import BaseDBManager
from app.database.models import (
    Materials,
    ProjectMaterials,
    ShiftReportMaterials,
    WorkMaterialRelations,
    Acceptances,
    WorkAcceptanceRelations,
    AcceptanceStatusHistory,
)

logger = logging.getLogger("ok_service")


class MaterialsManager(BaseDBManager):
    @property
    def model(self):
        return Materials


class WorkMaterialRelationsManager(BaseDBManager):
    @property
    def model(self):
        return WorkMaterialRelations


class ProjectMaterialsManager(BaseDBManager):
    @property
    def model(self):
        return ProjectMaterials


class ShiftReportMaterialsManager(BaseDBManager):
    @property
    def model(self):
        return ShiftReportMaterials


class AcceptancesManager(BaseDBManager):
    @property
    def model(self):
        return Acceptances

    def update_with_status_history(
        self, acceptance_id, *, date, project_id, status, comment,
        history_id, changed_at, changed_by, from_status, to_status
    ):
        with self.session_scope() as session:
            record = session.query(self.model).filter(self.model.id == acceptance_id).first()
            if record is None:
                return None
            record.date = date
            record.project_id = project_id
            record.status = status
            record.comment = comment
            session.add(AcceptanceStatusHistory(
                id=history_id,
                acceptance_id=acceptance_id,
                changed_at=changed_at,
                changed_by=changed_by,
                from_status=from_status,
                to_status=to_status,
            ))
            session.flush()
            return record.to_dict()

    def get_status_history(self, acceptance_id, *, offset=0, limit=1000):
        with self.session_scope() as session:
            records = (
                session.query(AcceptanceStatusHistory)
                .filter(AcceptanceStatusHistory.acceptance_id == acceptance_id)
                .order_by(AcceptanceStatusHistory.changed_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [record.to_dict() for record in records]

    def get_project_id(self, acceptance_id):
        with self.session_scope() as session:
            return session.query(self.model.project_id).filter(
                self.model.id == acceptance_id
            ).scalar()


class WorkAcceptanceRelationsManager(BaseDBManager):
    @property
    def model(self):
        return WorkAcceptanceRelations

    def get_project_id(self, relation_id):
        with self.session_scope() as session:
            record = (
                session.query(WorkAcceptanceRelations)
                .join(Acceptances)
                .filter(WorkAcceptanceRelations.id == relation_id)
                .first()
            )
            return record.acceptance.project_id if record is not None else None
