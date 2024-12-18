from app.database.models import Projects, ProjectSchedules, ProjectWorks
# Предполагается, что BaseDBManager в другом файле
from app.database.managers.abstract_manager import BaseDBManager


class ProjectsManager(BaseDBManager):

    @property
    def model(self):
        return Projects


class ProjectSchedulesManager(BaseDBManager):

    @property
    def model(self):
        return ProjectSchedules


class ProjectWorksManager(BaseDBManager):

    @property
    def model(self):
        return ProjectWorks
