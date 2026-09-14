# Предполагается, что BaseDBManager в другом файле
from app.database.managers.abstract_manager import BaseDBManager
from app.database.models import Objects, ObjectStatuses, Places, Projects


class ObjectsManager(BaseDBManager):
    @property
    def model(self):
        return Objects

    def update_with_projects_closed(self, record_id, **data):
        with self.session_scope() as session:
            obj = (
                session.query(Objects)
                .filter(Objects.object_id == record_id)
                .with_for_update()
                .first()
            )
            if obj is None:
                return None
            projects = (
                session.query(Projects)
                .filter(Projects.object == record_id, Projects.deleted.is_(False))
                .with_for_update()
                .all()
            )
            if any(
                (project.status.value if hasattr(project.status, "value") else project.status)
                != "closed"
                for project in projects
            ):
                raise ValueError(
                    "Object can be completed only when all its projects are closed"
                )
            for field, value in data.items():
                setattr(obj, field, value)
            session.flush()
            return obj.to_dict()


class ObjectStatusesManager(BaseDBManager):
    @property
    def model(self):
        return ObjectStatuses


class PlacesManager(BaseDBManager):
    @property
    def model(self):
        return Places
