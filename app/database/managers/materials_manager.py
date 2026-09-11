import logging
from decimal import Decimal

from app.database.managers.abstract_manager import BaseDBManager
from app.database.models import (
    Acceptances,
    AcceptanceStatusHistory,
    Materials,
    Objects,
    ProjectMaterials,
    Projects,
    ShiftReportMaterials,
    WorkAcceptanceRelations,
    WorkMaterialRelations,
    ProjectWorks,
)
from app.domain.work_acceptance_relations import WorkAcceptanceQuantityExceededError

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
        self,
        acceptance_id,
        *,
        date,
        project_id,
        status,
        comment,
        history_id,
        changed_at,
        changed_by,
        from_status,
        to_status,
    ):
        with self.session_scope() as session:
            record = (
                session.query(self.model).filter(self.model.id == acceptance_id).first()
            )
            if record is None:
                return None
            self._ensure_project_object_not_waiting(session, project_id)
            record.date = date
            record.project_id = project_id
            record.status = status
            record.comment = comment
            session.add(
                AcceptanceStatusHistory(
                    id=history_id,
                    acceptance_id=acceptance_id,
                    changed_at=changed_at,
                    changed_by=changed_by,
                    from_status=from_status,
                    to_status=to_status,
                )
            )
            session.flush()
            return record.to_dict()

    @staticmethod
    def _ensure_project_object_not_waiting(session, project_id):
        object_status = (
            session.query(Objects.status)
            .join(Projects, Projects.object == Objects.object_id)
            .filter(Projects.project_id == project_id, Projects.deleted.is_(False))
            .scalar()
        )
        if object_status == "waiting":
            raise ValueError(
                "Acceptances cannot be created or edited while the object is waiting"
            )

    def get_project_object_status(self, project_id):
        with self.session_scope() as session:
            return (
                session.query(Objects.status)
                .join(Projects, Projects.object == Objects.object_id)
                .filter(Projects.project_id == project_id, Projects.deleted.is_(False))
                .scalar()
            )

    def get_project_leader_id(self, project_id):
        with self.session_scope() as session:
            return (
                session.query(Projects.project_leader)
                .join(Acceptances, Acceptances.project_id == Projects.project_id)
                .filter(Projects.project_id == project_id)
                .scalar()
            )

    def get_all_filtered(
        self,
        *,
        offset=0,
        limit=None,
        project_id=None,
        status=None,
        project_leader_id=None,
        **filters,
    ):
        with self.session_scope() as session:
            query = session.query(self.model)
            if project_leader_id is not None:
                query = query.join(
                    Projects, self.model.project_id == Projects.project_id
                )
                query = query.filter(Projects.project_leader == project_leader_id)
            if project_id is not None:
                query = query.filter(self.model.project_id == project_id)
            if status is not None:
                query = query.filter(self.model.status == status)
            query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            return [record.to_dict() for record in query.all()]

    def add(self, **kwargs):
        with self.session_scope() as session:
            self._ensure_project_object_not_waiting(session, kwargs["project_id"])
            new_record = self.model(**kwargs)
            session.add(new_record)
            session.flush()
            return new_record.to_dict()

    def update(self, record_id, **kwargs):
        filtered_kwargs = {
            key: value
            for key, value in kwargs.items()
            if value is not None or key == "comment"
        }
        if not filtered_kwargs:
            return None
        with self.session_scope() as session:
            record = (
                session.query(self.model).filter(self.model.id == record_id).first()
            )
            if record is None:
                return None
            self._ensure_project_object_not_waiting(
                session, filtered_kwargs.get("project_id", record.project_id)
            )
            for field, value in filtered_kwargs.items():
                setattr(record, field, value)
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
            return (
                session.query(self.model.project_id)
                .filter(self.model.id == acceptance_id)
                .scalar()
            )


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

    @staticmethod
    def _ensure_quantity_available(
        session, relation, *, exclude_relation_id=None
    ):
        project_id = (
            session.query(Acceptances.project_id)
            .filter(Acceptances.id == relation.acceptance_id)
            .scalar()
        )
        if project_id is None:
            return

        # Lock every matching specification row. A missing work has a zero
        # limit and cannot be accepted, so it does not need a lock.
        specification_rows = (
            session.query(ProjectWorks.quantity)
            .filter(
                ProjectWorks.project == project_id,
                ProjectWorks.work == relation.work_id,
            )
            .with_for_update()
            .all()
        )
        specification_quantity = sum(
            (Decimal(str(row.quantity)) for row in specification_rows),
            Decimal("0"),
        )
        accepted_query = (
            session.query(WorkAcceptanceRelations.quantity)
            .join(
                Acceptances,
                Acceptances.id == WorkAcceptanceRelations.acceptance_id,
            )
            .filter(
                Acceptances.project_id == project_id,
                WorkAcceptanceRelations.work_id == relation.work_id,
            )
        )
        if exclude_relation_id is not None:
            accepted_query = accepted_query.filter(
                WorkAcceptanceRelations.id != exclude_relation_id
            )
        accepted_quantity = sum(
            (Decimal(str(row.quantity)) for row in accepted_query.all()),
            Decimal("0"),
        )
        available_quantity = specification_quantity - accepted_quantity
        exceeded_quantity = relation.quantity - available_quantity
        if exceeded_quantity > 0:
            raise WorkAcceptanceQuantityExceededError(
                work_id=relation.work_id,
                specification_quantity=specification_quantity,
                available_quantity=available_quantity,
                requested_quantity=relation.quantity,
                exceeded_quantity=exceeded_quantity,
            )

    def add_with_quantity_check(self, **kwargs):
        with self.session_scope() as session:
            relation = self.model(**kwargs)
            self._ensure_quantity_available(session, relation)
            session.add(relation)
            session.flush()
            return relation.to_dict()

    def update_with_quantity_check(self, record_id, **kwargs):
        filtered_kwargs = {
            key: value for key, value in kwargs.items() if value is not None
        }
        if not filtered_kwargs:
            return None
        with self.session_scope() as session:
            relation = (
                session.query(self.model)
                .filter(self.model.id == record_id)
                .first()
            )
            if relation is None:
                return None
            for field, value in filtered_kwargs.items():
                setattr(relation, field, value)
            self._ensure_quantity_available(
                session, relation, exclude_relation_id=record_id
            )
            session.flush()
            return relation.to_dict()
