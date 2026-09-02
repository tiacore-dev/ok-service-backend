from uuid import UUID, uuid4

from app.database.managers.projects_managers import ProjectsManager
from app.database.models import Acceptances, ProjectWorks, WorkAcceptanceRelations


def test_acceptance_quantity_is_not_multiplied_by_duplicate_project_works(
    db_session, seed_project, seed_work, seed_user
):
    project_id = UUID(seed_project["project_id"])
    work_id = UUID(seed_work["work_id"])
    user_id = UUID(seed_user["user_id"])

    db_session.add_all(
        [
            ProjectWorks(
                project_work_id=uuid4(),
                project_work_name="Первый объём",
                work=work_id,
                project=project_id,
                quantity=10,
                price=10,
                summ=100,
                created_by=user_id,
            ),
            ProjectWorks(
                project_work_id=uuid4(),
                project_work_name="Второй объём",
                work=work_id,
                project=project_id,
                quantity=20,
                price=10,
                summ=200,
                created_by=user_id,
            ),
        ]
    )
    acceptance = Acceptances(
        id=uuid4(),
        date=20260901,
        project_id=project_id,
        status="documents_signed",
    )
    db_session.add(acceptance)
    db_session.flush()
    db_session.add(
        WorkAcceptanceRelations(
            id=uuid4(),
            acceptance_id=acceptance.id,
            work_id=work_id,
            quantity=5,
        )
    )
    db_session.commit()

    stats = ProjectsManager().get_project_stats(project_id)[str(work_id)]

    assert stats["presented_quantity"] == 5.0
    assert stats["accepted_quantity"] == 5.0
    assert stats["presented_summ"] == 50.0
    assert stats["accepted_summ"] == 50.0
