from dataclasses import dataclass, field
from uuid import UUID

from app.database.managers.objects_managers import PlacesManager
from app.database.managers.place_relations_manager import (
    ProjectPlaceRelationsManager,
    ShiftPlaceRelationsManager,
)
from app.database.managers.projects_managers import ProjectsManager
from app.database.managers.shift_reports_managers import ShiftReportsManager
from app.use_cases.place_relations import (
    PlaceRelationRepository,
    ProjectPlaceRelation,
    ShiftPlaceRelation,
    ShiftContext,
)


def _project(value):
    return ProjectPlaceRelation(
        UUID(value["project_place_relation_id"]),
        UUID(value["project_id"]),
        UUID(value["place_id"]),
    )


def _shift(value):
    return ShiftPlaceRelation(
        UUID(value["shift_place_relation_id"]),
        UUID(value["shift_report_id"]),
        UUID(value["place_id"]),
        value.get("comment"),
    )


@dataclass(slots=True)
class SQLAlchemyPlaceRelationRepository(PlaceRelationRepository):
    project_manager: ProjectPlaceRelationsManager = field(
        default_factory=ProjectPlaceRelationsManager
    )
    shift_manager: ShiftPlaceRelationsManager = field(
        default_factory=ShiftPlaceRelationsManager
    )
    projects_manager: ProjectsManager = field(default_factory=ProjectsManager)
    places_manager: PlacesManager = field(default_factory=PlacesManager)
    reports_manager: ShiftReportsManager = field(default_factory=ShiftReportsManager)

    def get_project_place_relation(self, relation_id):
        value = self.project_manager.get_by_id(relation_id)
        return _project(value) if value else None

    def create_project_place_relation(self, relation):
        return _project(
            self.project_manager.add(
                project_place_relation_id=relation.project_place_relation_id,
                project_id=relation.project_id,
                place_id=relation.place_id,
            )
        )

    def update_project_place_relation(self, relation):
        value = self.project_manager.update(
            record_id=relation.project_place_relation_id,
            project_id=relation.project_id,
            place_id=relation.place_id,
        )
        return _project(value) if value else None

    def delete_project_place_relation(self, relation_id):
        return self.project_manager.delete(relation_id) is not None

    def list_project_place_relations(self):
        return [_project(value) for value in self.project_manager.get_all()]

    def get_shift_place_relation(self, relation_id):
        value = self.shift_manager.get_by_id(relation_id)
        return _shift(value) if value else None

    def create_shift_place_relation(self, relation):
        return _shift(
            self.shift_manager.add(
                shift_place_relation_id=relation.shift_place_relation_id,
                shift_report_id=relation.shift_report_id,
                place_id=relation.place_id,
                comment=relation.comment,
            )
        )

    def update_shift_place_relation(self, relation):
        value = self.shift_manager.update(
            record_id=relation.shift_place_relation_id,
            shift_report_id=relation.shift_report_id,
            place_id=relation.place_id,
            comment=relation.comment,
        )
        return _shift(value) if value else None

    def delete_shift_place_relation(self, relation_id):
        return self.shift_manager.delete(relation_id) is not None

    def list_shift_place_relations(self):
        return [_shift(value) for value in self.shift_manager.get_all()]

    def project_object_id(self, project_id):
        value = self.projects_manager.get_by_id(project_id)
        return UUID(value["object"]) if value else None

    def place_object_id(self, place_id):
        value = self.places_manager.get_by_id(place_id)
        if not value:
            return None
        return UUID(value["object_id"])

    def place_response(self, place_id):
        value = self.places_manager.get_by_id(place_id)
        if value is None:
            return None
        return value

    def project_leader_id(self, project_id):
        value = self.projects_manager.get_by_id(project_id)
        return (
            UUID(value["project_leader"])
            if value and value.get("project_leader")
            else None
        )

    def shift_context(self, shift_report_id):
        value = self.reports_manager.get_by_id(shift_report_id)
        return (
            ShiftContext(
                project_id=UUID(value["project"]),
                user_id=UUID(value["user"]),
                signed=bool(value.get("signed", False)),
            )
            if value
            else None
        )

    def has_project_place(self, project_id, place_id):
        return bool(
            self.project_manager.exists(project_id=project_id, place_id=place_id)
        )

    def has_shift_place(self, shift_report_id, place_id):
        return bool(
            self.shift_manager.exists(
                shift_report_id=shift_report_id, place_id=place_id
            )
        )

    def is_place_used_by_shift(self, project_id, place_id):
        with self.shift_manager.session_scope() as session:
            from app.database.models import ShiftReports

            return (
                session.query(self.shift_manager.model)
                .join(ShiftReports)
                .filter(
                    ShiftReports.project == project_id,
                    self.shift_manager.model.place_id == place_id,
                )
                .first()
                is not None
            )

    def bulk_create_project_place_relations(self, relations):
        with self.project_manager.session_scope() as session:
            records = [
                self.project_manager.model(
                    project_place_relation_id=item.project_place_relation_id,
                    project_id=item.project_id,
                    place_id=item.place_id,
                )
                for item in relations
            ]
            session.add_all(records)
            session.flush()
            return [_project(record.to_dict()) for record in records]

    def bulk_delete_project_place_relations(self, relation_ids):
        with self.project_manager.session_scope() as session:
            deleted = (
                session.query(self.project_manager.model)
                .filter(
                    self.project_manager.model.project_place_relation_id.in_(
                        relation_ids
                    )
                )
                .delete(synchronize_session=False)
            )
            session.flush()
            return deleted

    def bulk_create_shift_place_relations(self, relations):
        with self.shift_manager.session_scope() as session:
            records = [
                self.shift_manager.model(
                    shift_place_relation_id=item.shift_place_relation_id,
                    shift_report_id=item.shift_report_id,
                    place_id=item.place_id,
                    comment=item.comment,
                )
                for item in relations
            ]
            session.add_all(records)
            session.flush()
            return [_shift(record.to_dict()) for record in records]

    def bulk_delete_shift_place_relations(self, relation_ids):
        with self.shift_manager.session_scope() as session:
            deleted = (
                session.query(self.shift_manager.model)
                .filter(
                    self.shift_manager.model.shift_place_relation_id.in_(relation_ids)
                )
                .delete(synchronize_session=False)
            )
            session.flush()
            return deleted

    def ensure_project_object(self, project_id, object_id):
        if any(
            self.place_object_id(item.place_id) != object_id
            for item in self.list_project_place_relations()
            if item.project_id == project_id
        ):
            from app.use_cases.place_relations import PlaceRelationConflictError

            raise PlaceRelationConflictError(
                "Project object conflicts with selected places"
            )

    def ensure_place_object(self, place_id, object_id):
        if any(
            self.project_object_id(item.project_id) != object_id
            for item in self.list_project_place_relations()
            if item.place_id == place_id
        ):
            from app.use_cases.place_relations import PlaceRelationConflictError

            raise PlaceRelationConflictError(
                "Place object conflicts with selected projects"
            )

    def ensure_shift_project(self, shift_report_id, project_id):
        if any(
            not self.has_project_place(project_id, item.place_id)
            for item in self.list_shift_place_relations()
            if item.shift_report_id == shift_report_id
        ):
            from app.use_cases.place_relations import PlaceRelationConflictError

            raise PlaceRelationConflictError(
                "Shift project conflicts with selected places"
            )
