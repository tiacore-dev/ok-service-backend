from app.models import Projects, ProjectSchedules, ProjectWorks
from app.database.managers.abstract_manager import BaseDBManager  # Предполагается, что BaseDBManager в другом файле


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