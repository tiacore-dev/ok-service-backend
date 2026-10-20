"""PostgreSQL checks runnable with --noconftest and TEST_DATABASE_URL.

Each check uses its own schema in an outer transaction; no existing tables or
application data are touched.
"""

import importlib.util
import os
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.project_materials.mappers import project_material_dict_to_entity
from app.database.db_setup import Base
from app.database.managers.materials_manager import (
    ProjectMaterialsManager,
    ShiftReportMaterialsManager,
)
from app.database.managers.project_material_matching import find_project_material_id
from app.database.managers.projects_managers import ProjectsManager, ProjectWorksManager
from app.database.managers.shift_reports_managers import (
    ShiftReportsDetailsManager,
    ShiftReportsManager,
)
from app.database.models import (
    Materials,
    Objects,
    ProjectMaterials,
    Projects,
    ProjectWorks,
    Roles,
    ShiftReportDetails,
    ShiftReportMaterials,
    ShiftReports,
    Users,
    WorkMaterialRelations,
    Works,
)
from app.domain.project_materials import ProjectMaterialInUseError
from app.domain.shift_report_materials import ShiftReportMaterialValidationError
from app.domain.shift_reports import ShiftReportConflictError
from app.web.project_materials.routes import _map_error


@pytest.fixture
def link_session():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL checks")
    engine = create_engine(url)
    with engine.connect() as connection:
        transaction = connection.begin()
        schema = "material_link_" + uuid4().hex
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        Base.metadata.create_all(connection)
        with Session(
            bind=connection, join_transaction_mode="create_savepoint"
        ) as session:
            yield session
        transaction.rollback()
    engine.dispose()


@pytest.fixture
def scenario(link_session):
    session = link_session
    user_id = uuid4()
    session.add(Roles(role_id="project-leader", name="Leader"))
    session.flush()
    user = Users(
        user_id=user_id,
        login="leader",
        name="Leader",
        role="project-leader",
        password_hash="unused",
        created_by=user_id,
    )
    session.add(user)
    session.flush()
    obj = Objects(name="Object", created_by=user_id)
    work = Works(name="Work", created_by=user_id)
    material = Materials(name="Material", created_by=user_id)
    session.add_all([obj, work, material])
    session.flush()
    project = Projects(
        name="Project",
        object=obj.object_id,
        project_leader=user_id,
        created_by=user_id,
        status="in_progress",
    )
    session.add(project)
    session.flush()
    project_work = ProjectWorks(
        project=project.project_id,
        work=work.work_id,
        quantity=Decimal(10),
        created_by=user_id,
    )
    report = ShiftReports(
        project=project.project_id,
        user=user_id,
        created_by=user_id,
        date=1792396800000,
        signed=True,
    )
    session.add_all([project_work, report])
    session.flush()
    detail = ShiftReportDetails(
        shift_report=report.shift_report_id,
        project_work=project_work.project_work_id,
        work=work.work_id,
        quantity=Decimal(3),
        summ=Decimal(0),
        created_by=user_id,
    )
    relation = WorkMaterialRelations(
        work=work.work_id,
        material=material.material_id,
        quantity=Decimal(2),
        created_by=user_id,
    )
    session.add_all([detail, relation])
    session.flush()
    return SimpleNamespace(
        user=user,
        project=project,
        work=work,
        material=material,
        project_work=project_work,
        report=report,
        detail=detail,
        relation=relation,
    )


def specification(
    session, scenario, *, created_at=1, price: str | None = "7", **overrides
):
    values = {
        "project": scenario.project.project_id,
        "project_work": scenario.project_work.project_work_id,
        "material": scenario.material.material_id,
        "quantity": Decimal(10),
        "price": Decimal(price) if price is not None else None,
        "summ": Decimal(price) * 10 if price is not None else None,
        "created_at": created_at,
        "created_by": scenario.user.user_id,
        "project_material_name": "Saved name",
    }
    values.update(overrides)
    row = ProjectMaterials(**values)
    session.add(row)
    session.flush()
    return row


def add_actual(session, scenario, **overrides):
    project_material = (
        session.query(ProjectMaterials)
        .order_by(ProjectMaterials.created_at, ProjectMaterials.project_material_id)
        .first()
    )
    assert project_material is not None
    values = {
        "shift_report": scenario.report.shift_report_id,
        "project_material": project_material.project_material_id,
        "shift_report_detail": scenario.detail.shift_report_detail_id,
        "quantity": Decimal(3),
        "created_by": scenario.user.user_id,
    }
    values.update(overrides)
    return ShiftReportMaterialsManager(session=session).add(**values)


def test_manual_and_automatic_actuals_choose_earliest_specification(
    link_session, scenario
):
    specification(link_session, scenario, created_at=20, price="100")
    earliest = specification(link_session, scenario, created_at=10)
    record = add_actual(link_session, scenario)
    assert record["project_material"] == str(earliest.project_material_id)

    ShiftReportsDetailsManager._sync_shift_report_materials(
        link_session, scenario.detail, scenario.user.user_id
    )
    link_session.flush()
    rows = link_session.query(ShiftReportMaterials).all()
    assert len(rows) == 1
    assert rows[0].project_material == earliest.project_material_id
    assert rows[0].quantity == Decimal(6)


def test_equal_timestamps_choose_smallest_uuid(link_session, scenario):
    specification(link_session, scenario, project_material_id=UUID(int=2))
    first = specification(link_session, scenario, project_material_id=UUID(int=1))
    assert (
        find_project_material_id(
            link_session,
            scenario.report.shift_report_id,
            scenario.material.material_id,
            scenario.detail.shift_report_detail_id,
        )
        == first.project_material_id
    )


@pytest.mark.parametrize(
    "missing", ["project_work", "other_report", "other_project", "missing_id"]
)
def test_explicit_project_material_rejects_incompatible_context(
    link_session, scenario, missing
):
    row = specification(link_session, scenario)
    actual = {}
    if missing == "project_work":
        scenario.detail.project_work = None
        link_session.flush()
    elif missing == "other_report":
        report = ShiftReports(
            project=scenario.project.project_id,
            user=scenario.user.user_id,
            created_by=scenario.user.user_id,
            date=1792483200000,
        )
        link_session.add(report)
        link_session.flush()
        actual["shift_report"] = report.shift_report_id
    elif missing == "other_project":
        project = Projects(
            name="Other",
            object=scenario.project.object,
            created_by=scenario.user.user_id,
        )
        link_session.add(project)
        link_session.flush()
        row.project = project.project_id
        link_session.flush()
    else:
        actual["project_material"] = uuid4()
    with pytest.raises(ShiftReportMaterialValidationError):
        add_actual(link_session, scenario, **actual)
    assert link_session.query(ShiftReportMaterials).count() == 0


def test_explicit_project_material_does_not_require_detail(link_session, scenario):
    row = specification(link_session, scenario)
    actual = add_actual(link_session, scenario, shift_report_detail=None)
    assert actual["project_material"] == str(row.project_material_id)


def test_edit_project_material_and_quantity(link_session, scenario):
    first = specification(link_session, scenario)
    second = specification(link_session, scenario, created_at=2)
    record = add_actual(link_session, scenario)
    manager = ShiftReportMaterialsManager(session=link_session)
    record_id = UUID(record["shift_report_material_id"])
    quantity_updated = manager.update(record_id, quantity=Decimal(4))
    assert quantity_updated is not None
    assert quantity_updated["project_material"] == str(first.project_material_id)
    material_updated = manager.update(
        record_id, project_material=second.project_material_id
    )
    assert material_updated is not None
    assert material_updated["project_material"] == str(second.project_material_id)


@pytest.mark.parametrize("with_actual", [False, True])
def test_missing_specification_rejects_detail_operation_atomically(
    link_session, scenario, with_actual
):
    if with_actual:
        specification(link_session, scenario)
        add_actual(link_session, scenario)
        # A second normative material is missing from the specification.
        other = Materials(name="Missing", created_by=scenario.user.user_id)
        link_session.add(other)
        link_session.flush()
        link_session.add(
            WorkMaterialRelations(
                work=scenario.work.work_id,
                material=other.material_id,
                quantity=1,
                created_by=scenario.user.user_id,
            )
        )
        link_session.flush()
    before = [
        (row.shift_report_material_id, row.project_material, row.quantity)
        for row in link_session.query(ShiftReportMaterials).all()
    ]
    previous_quantity = scenario.detail.quantity
    with pytest.raises(ShiftReportConflictError), link_session.begin_nested():
        scenario.detail.quantity = Decimal(8)
        link_session.flush()
        ShiftReportsDetailsManager._sync_shift_report_materials(
            link_session, scenario.detail, scenario.user.user_id
        )
        link_session.flush()
    assert scenario.detail.quantity == previous_quantity
    assert [
        (row.shift_report_material_id, row.project_material, row.quantity)
        for row in link_session.query(ShiftReportMaterials).all()
    ] == before


def test_specification_sync_keeps_id_price_name_and_other_matching_rows(
    link_session, scenario
):
    later = specification(link_session, scenario, created_at=20, price="99")
    earlier = specification(link_session, scenario, created_at=10)
    original = project_material_dict_to_entity(earlier.to_dict())
    add_actual(link_session, scenario)
    scenario.project_work.quantity = Decimal(11)
    ProjectWorksManager(session=link_session)._sync_project_materials(
        link_session, scenario.project_work, scenario.user.user_id
    )
    updated = project_material_dict_to_entity(earlier.to_dict())
    unchanged = project_material_dict_to_entity(later.to_dict())
    assert updated.project_material_id == original.project_material_id
    assert updated.quantity == Decimal(22)
    assert updated.price == Decimal(7)
    assert updated.summ == Decimal(154)
    assert updated.project_material_name == "Saved name"
    assert updated.created_at == 10
    assert updated.created_by == original.created_by
    assert unchanged.quantity == Decimal(10)
    assert link_session.query(ProjectMaterials).count() == 2
    assert str(link_session.query(ShiftReportMaterials).one().project_material) == str(
        original.project_material_id
    )


def test_specification_sync_creates_missing_rows(link_session, scenario):
    ProjectWorksManager(session=link_session)._sync_project_materials(
        link_session, scenario.project_work, scenario.user.user_id
    )
    row = link_session.query(ProjectMaterials).one()
    assert row.quantity == Decimal(20)
    assert row.price is None


@pytest.mark.parametrize("operation", ["delete", "orm_delete", "sync", "delete_work"])
def test_used_specification_cannot_be_deleted(link_session, scenario, operation):
    row = specification(link_session, scenario)
    add_actual(link_session, scenario)
    with pytest.raises(IntegrityError) as error, link_session.begin_nested():
        if operation == "delete":
            ProjectMaterialsManager(session=link_session).delete(
                row.project_material_id
            )
        elif operation == "orm_delete":
            # Loaded children must not be silently detached by SQLAlchemy.
            assert row.shift_report_materials
            link_session.delete(row)
            link_session.flush()
        elif operation == "delete_work":
            ProjectWorksManager(session=link_session).delete(
                scenario.project_work.project_work_id
            )
        else:
            link_session.delete(scenario.relation)
            link_session.flush()
            ProjectWorksManager(session=link_session)._sync_project_materials(
                link_session, scenario.project_work, scenario.user.user_id
            )
    assert _map_error(error.value)[1] == 409
    assert link_session.query(ShiftReportMaterials).count() == 1
    assert link_session.query(ProjectMaterials).count() == 1


def test_unused_specification_can_be_deleted(link_session, scenario):
    row = specification(link_session, scenario)
    assert ProjectMaterialsManager(session=link_session).delete(row.project_material_id)
    assert link_session.query(ProjectMaterials).count() == 0


def test_unused_obsolete_specification_is_removed_by_sync(link_session, scenario):
    specification(link_session, scenario)
    link_session.delete(scenario.relation)
    link_session.flush()
    ProjectWorksManager(session=link_session)._sync_project_materials(
        link_session, scenario.project_work, scenario.user.user_id
    )
    assert link_session.query(ProjectMaterials).count() == 0


def test_used_specification_cannot_move_with_project_work(link_session, scenario):
    specification(link_session, scenario)
    add_actual(link_session, scenario)
    other = Projects(
        name="Other", object=scenario.project.object, created_by=scenario.user.user_id
    )
    link_session.add(other)
    link_session.flush()
    with pytest.raises(ProjectMaterialInUseError), link_session.begin_nested():
        ProjectWorksManager(session=link_session).update(
            scenario.project_work.project_work_id, project=other.project_id
        )
    assert (
        link_session.query(ProjectMaterials).one().project
        == scenario.project.project_id
    )


def test_moving_shift_to_other_project_rejects_incompatible_link(
    link_session, scenario
):
    specification(link_session, scenario)
    add_actual(link_session, scenario)
    other = Projects(
        name="Other", object=scenario.project.object, created_by=scenario.user.user_id
    )
    link_session.add(other)
    link_session.flush()
    original = scenario.report.project
    with pytest.raises(ShiftReportConflictError), link_session.begin_nested():
        ShiftReportsManager(session=link_session).update_shift_report(
            scenario.report.shift_report_id, project=other.project_id
        )
    assert scenario.report.project == original
    assert link_session.query(ShiftReportMaterials).one().project_material is not None


@pytest.mark.parametrize(
    "signed,deleted,expected", [(True, False, 42), (False, False, 0), (True, True, 0)]
)
def test_statistics_use_linked_price_without_multiplying_actuals(
    link_session, scenario, signed, deleted, expected
):
    specification(link_session, scenario, created_at=2, price="100")
    first = specification(link_session, scenario, created_at=1, price="7")
    add_actual(link_session, scenario, quantity=Decimal(4))
    add_actual(link_session, scenario, quantity=Decimal(2), shift_report_detail=None)
    scenario.report.signed = signed
    scenario.report.deleted = deleted
    link_session.flush()
    manager = ProjectsManager(session=link_session)
    result = manager.get_project_material_stats(scenario.project.project_id)[
        str(scenario.material.material_id)
    ]
    assert result["shift_report_material_summ_by_estimate"] == expected
    assert result["shift_report_material_quantity"] == (
        6 if signed and not deleted else 0
    )
    monthly = manager.get_all_project_leaders_fact_stats()
    totals = monthly["material_totals"]
    assert (
        sum(item["shift_report_material_summ_by_estimate"] for item in totals.values())
        == expected
    )
    assert project_material_dict_to_entity(first.to_dict()).price == Decimal(7)


def test_missing_price_keeps_actual_quantity_with_zero_estimate(link_session, scenario):
    specification(link_session, scenario, price=None)
    add_actual(link_session, scenario)
    result = ProjectsManager(session=link_session).get_project_material_stats(
        scenario.project.project_id
    )
    assert (
        result[str(scenario.material.material_id)]["shift_report_material_quantity"]
        == 3
    )
    assert (
        result[str(scenario.material.material_id)][
            "shift_report_material_summ_by_estimate"
        ]
        == 0
    )


def load_migration(filename):
    path = Path(__file__).parents[1] / "alembic/versions" / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "unmatched_reason",
    ["no_detail", "no_project_work", "missing_material", "other_project"],
)
def test_migration_matches_usage_and_deletes_only_unmatched(
    link_session, scenario, unmatched_reason, caplog
):
    specification(link_session, scenario, created_at=20, price="100")
    earliest = specification(link_session, scenario, created_at=10)
    tied = specification(link_session, scenario, created_at=10)
    selected = min((earliest.project_material_id, tied.project_material_id))
    linked = add_actual(link_session, scenario)
    unlinked = add_actual(link_session, scenario, shift_report_detail=None)
    connection = link_session.connection()
    initial = load_migration(
        "20261019140000_link_shift_materials_to_project_materials.py"
    )
    final = load_migration("20261019150000_require_shift_project_material.py")
    with Operations.context(MigrationContext.configure(connection)):
        final.downgrade()
        initial.downgrade()
        if unmatched_reason != "no_detail":
            # Build representative legacy rows without consulting the new ORM field.
            if unmatched_reason == "no_project_work":
                legacy_detail = uuid4()
                connection.execute(
                    text("""
                    INSERT INTO shift_report_details
                    (shift_report_detail_id, shift_report, work, quantity, summ, created_at, created_by)
                    VALUES (:id, :report, :work, 1, 0, 1, :creator)
                """),
                    {
                        "id": legacy_detail,
                        "report": scenario.report.shift_report_id,
                        "work": scenario.work.work_id,
                        "creator": scenario.user.user_id,
                    },
                )
                connection.execute(
                    text(
                        "UPDATE shift_report_materials SET shift_report_detail=:detail WHERE shift_report_material_id=:id"
                    ),
                    {
                        "detail": legacy_detail,
                        "id": UUID(unlinked["shift_report_material_id"]),
                    },
                )
            elif unmatched_reason == "missing_material":
                other_material = uuid4()
                connection.execute(
                    text(
                        "INSERT INTO materials (material_id, name, created_by, deleted) VALUES (:id, 'Missing', :creator, false)"
                    ),
                    {"id": other_material, "creator": scenario.user.user_id},
                )
                connection.execute(
                    text(
                        "UPDATE shift_report_materials SET material=:material, shift_report_detail=:detail WHERE shift_report_material_id=:id"
                    ),
                    {
                        "material": other_material,
                        "detail": scenario.detail.shift_report_detail_id,
                        "id": UUID(unlinked["shift_report_material_id"]),
                    },
                )
            else:
                other_project, other_report, other_detail = uuid4(), uuid4(), uuid4()
                connection.execute(
                    text("""
                    INSERT INTO projects (project_id, name, object, created_by, deleted, night_shift_available, extreme_conditions_available, status)
                    VALUES (:id, 'Other project', :object, :creator, false, false, false, 'in_progress')
                """),
                    {
                        "id": other_project,
                        "object": scenario.project.object,
                        "creator": scenario.user.user_id,
                    },
                )
                connection.execute(
                    text("""
                    INSERT INTO shift_reports (shift_report_id, project, \"user\", date, created_at, created_by, signed, deleted, night_shift, extreme_conditions, short_shift)
                    VALUES (:id, :project, :creator, 1, 1, :creator, false, false, false, false, false)
                """),
                    {
                        "id": other_report,
                        "project": other_project,
                        "creator": scenario.user.user_id,
                    },
                )
                connection.execute(
                    text("""
                    INSERT INTO shift_report_details (shift_report_detail_id, shift_report, project_work, work, quantity, summ, created_at, created_by)
                    VALUES (:id, :report, :project_work, :work, 1, 0, 1, :creator)
                """),
                    {
                        "id": other_detail,
                        "report": other_report,
                        "project_work": scenario.project_work.project_work_id,
                        "work": scenario.work.work_id,
                        "creator": scenario.user.user_id,
                    },
                )
                connection.execute(
                    text(
                        "UPDATE shift_report_materials SET shift_report=:report, shift_report_detail=:detail WHERE shift_report_material_id=:id"
                    ),
                    {
                        "report": other_report,
                        "detail": other_detail,
                        "id": UUID(unlinked["shift_report_material_id"]),
                    },
                )
        before = connection.execute(
            text(
                "SELECT * FROM shift_report_materials ORDER BY shift_report_material_id"
            )
        ).all()
        initial.upgrade()
        mapped = dict(
            connection.execute(
                text(
                    "SELECT shift_report_material_id, project_material FROM shift_report_materials"
                )
            ).all()
        )
        assert mapped[UUID(linked["shift_report_material_id"])] == selected
        assert mapped[UUID(unlinked["shift_report_material_id"])] is None
        with caplog.at_level("INFO", logger="alembic.runtime.migration"):
            final.upgrade()
        assert "Archived and removed 1 unmatched shift_report_materials" in caplog.text
        archived = connection.execute(text(
            "SELECT * FROM shift_report_materials_unmatched_archive"
        )).mappings().one()
        original_unlinked = next(
            row for row in before
            if str(row._mapping["shift_report_material_id"])
            == unlinked["shift_report_material_id"]
        )
        for field, value in original_unlinked._mapping.items():
            assert archived[field] == value
        assert archived["project_material"] is None
        assert archived["migration_revision"] == "20261019150000"
        assert archived["archived_at"] is not None
        assert archived["restored_at"] is None
        assert inspect(connection).get_foreign_keys(
            "shift_report_materials_unmatched_archive"
        ) == []
        columns = {
            column["name"]: column
            for column in inspect(connection).get_columns("shift_report_materials")
        }
        assert "material" not in columns
        assert columns["project_material"]["nullable"] is False
        remaining = connection.execute(
            text("SELECT * FROM shift_report_materials")
        ).mappings().one()
        original = next(
            row
            for row in before
            if str(row._mapping["shift_report_material_id"])
            == linked["shift_report_material_id"]
        )
        assert remaining["project_material"] == selected
        for field, value in original._mapping.items():
            if field != "material":
                assert remaining[field] == value
        # Downgrade restores the legacy schema and all archived usage.
        final.downgrade()
        initial.downgrade()
        restored = connection.execute(
            text("SELECT * FROM shift_report_materials ORDER BY shift_report_material_id")
        ).all()
        assert restored == before
        assert connection.execute(text(
            "SELECT restored_at FROM shift_report_materials_unmatched_archive"
        )).scalar_one() is not None


@pytest.mark.parametrize("with_usage", [False, True])
@pytest.mark.parametrize("stage", ["legacy", "nullable"])
def test_migration_with_resolved_usage_preserves_data_and_round_trips(
    link_session, scenario, with_usage, stage
):
    if with_usage:
        specification(link_session, scenario)
        add_actual(link_session, scenario)
    connection = link_session.connection()
    initial = load_migration(
        "20261019140000_link_shift_materials_to_project_materials.py"
    )
    final = load_migration("20261019150000_require_shift_project_material.py")
    with Operations.context(MigrationContext.configure(connection)):
        final.downgrade()
        if stage == "legacy":
            initial.downgrade()
            initial.upgrade()
        else:
            # Reproduce records awaiting a retry after the nullable stage.
            connection.execute(
                text("UPDATE shift_report_materials SET project_material = NULL")
            )
        before = connection.execute(
            text("SELECT * FROM shift_report_materials ORDER BY shift_report_material_id")
        ).all()
        final.upgrade()
        columns = {
            column["name"]: column
            for column in inspect(connection).get_columns("shift_report_materials")
        }
        assert "material" not in columns
        assert columns["project_material"]["nullable"] is False
        after = connection.execute(
            text("SELECT * FROM shift_report_materials ORDER BY shift_report_material_id")
        ).mappings().all()
        for old, new in zip(before, after, strict=True):
            for field, value in old._mapping.items():
                if field not in {"material", "project_material"}:
                    assert new[field] == value
            assert new["project_material"] is not None
        if with_usage:
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(
                    text("UPDATE shift_report_materials SET project_material = NULL")
                )
        final.downgrade()
        restored = connection.execute(
            text("SELECT * FROM shift_report_materials ORDER BY shift_report_material_id")
        ).mappings().all()
        for old, new in zip(before, restored, strict=True):
            for field, value in old._mapping.items():
                if field != "project_material":
                    assert new[field] == value
        initial.downgrade()
        assert "project_material" not in {
            column["name"]
            for column in inspect(connection).get_columns("shift_report_materials")
        }


def test_migration_preserves_manual_link_without_detail(link_session, scenario):
    row = specification(link_session, scenario)
    actual = add_actual(link_session, scenario, shift_report_detail=None)
    connection = link_session.connection()
    final = load_migration("20261019150000_require_shift_project_material.py")
    with Operations.context(MigrationContext.configure(connection)):
        final.downgrade()
        before = connection.execute(text("SELECT * FROM shift_report_materials")).one()
        final.upgrade()
        after = connection.execute(
            text("SELECT * FROM shift_report_materials")
        ).mappings().one()
        assert str(after["shift_report_material_id"]) == actual["shift_report_material_id"]
        assert after["project_material"] == row.project_material_id
        for field, value in before._mapping.items():
            if field != "material":
                assert after[field] == value


@pytest.mark.parametrize("signed,deleted", [(True, False), (False, False), (True, True)])
def test_migration_removes_all_unmatched_regardless_of_report_status(
    link_session, scenario, signed, deleted
):
    specification(link_session, scenario)
    for _ in range(21):
        add_actual(link_session, scenario, shift_report_detail=None)
    scenario.report.signed = signed
    scenario.report.deleted = deleted
    link_session.flush()
    connection = link_session.connection()
    final = load_migration("20261019150000_require_shift_project_material.py")
    with Operations.context(MigrationContext.configure(connection)):
        final.downgrade()
        connection.execute(
            text("UPDATE shift_report_materials SET project_material = NULL")
        )
        final.upgrade()
        assert connection.execute(
            text("SELECT count(*) FROM shift_report_materials")
        ).scalar_one() == 0
        # Removing usage does not remove reports, their details or specifications.
        for table in ("shift_reports", "shift_report_details", "project_materials"):
            assert connection.execute(
                text(f"SELECT count(*) FROM {table}")
            ).scalar_one() == 1
        final.downgrade()
        assert connection.execute(
            text("SELECT count(*) FROM shift_report_materials")
        ).scalar_one() == 21
        assert connection.execute(text("""
            SELECT count(*) FROM shift_report_materials_unmatched_archive
            WHERE restored_at IS NOT NULL
        """)).scalar_one() == 21


def test_migration_cleanup_rolls_back_with_transaction(link_session, scenario):
    specification(link_session, scenario)
    add_actual(link_session, scenario)
    unlinked = add_actual(link_session, scenario, shift_report_detail=None)
    connection = link_session.connection()
    final = load_migration("20261019150000_require_shift_project_material.py")
    with Operations.context(MigrationContext.configure(connection)):
        final.downgrade()
        connection.execute(
            text("""
                UPDATE shift_report_materials SET project_material = NULL
                WHERE shift_report_material_id = :id
            """),
            {"id": UUID(unlinked["shift_report_material_id"])},
        )
        before = connection.execute(
            text("SELECT * FROM shift_report_materials ORDER BY shift_report_material_id")
        ).all()
        with pytest.raises(RuntimeError, match="abort migration"), connection.begin_nested():
            final.upgrade()
            assert connection.execute(
                text("SELECT count(*) FROM shift_report_materials")
            ).scalar_one() == 1
            raise RuntimeError("abort migration")
        assert connection.execute(
            text("SELECT * FROM shift_report_materials ORDER BY shift_report_material_id")
        ).all() == before
        columns = {
            column["name"]: column
            for column in inspect(connection).get_columns("shift_report_materials")
        }
        assert "material" in columns
        assert columns["project_material"]["nullable"] is True


def test_archive_keeps_history_across_upgrade_downgrade_cycles(link_session, scenario):
    specification(link_session, scenario)
    add_actual(link_session, scenario, shift_report_detail=None)
    connection = link_session.connection()
    final = load_migration("20261019150000_require_shift_project_material.py")
    with Operations.context(MigrationContext.configure(connection)):
        final.downgrade()
        connection.execute(text("UPDATE shift_report_materials SET project_material = NULL"))
        before = connection.execute(text("SELECT * FROM shift_report_materials")).one()
        for cycle in range(1, 3):
            final.upgrade()
            assert connection.execute(text("""
                SELECT count(*) FROM shift_report_materials_unmatched_archive
                WHERE restored_at IS NULL
            """)).scalar_one() == 1
            final.downgrade()
            assert connection.execute(text("SELECT * FROM shift_report_materials")).one() == before
            assert connection.execute(text("""
                SELECT count(*) FROM shift_report_materials_unmatched_archive
                WHERE restored_at IS NOT NULL
            """)).scalar_one() == cycle


@pytest.mark.parametrize("conflict", ["uuid", "shift_report", "material", "created_by", "shift_report_detail"])
def test_archive_restore_conflicts_preserve_archive_and_schema(
    link_session, scenario, conflict
):
    specification(link_session, scenario)
    actual = add_actual(link_session, scenario, shift_report_detail=None)
    connection = link_session.connection()
    final = load_migration("20261019150000_require_shift_project_material.py")
    with Operations.context(MigrationContext.configure(connection)):
        final.downgrade()
        connection.execute(text("UPDATE shift_report_materials SET project_material = NULL"))
        final.upgrade()
        if conflict == "uuid":
            add_actual(
                link_session, scenario,
                shift_report_material_id=UUID(actual["shift_report_material_id"]),
                shift_report_detail=None,
            )
        else:
            # An archive has no FKs; a referenced entity may no longer exist.
            connection.execute(
                text(f"UPDATE shift_report_materials_unmatched_archive SET {conflict} = :id"),
                {"id": uuid4()},
            )
        archived = connection.execute(text(
            "SELECT * FROM shift_report_materials_unmatched_archive"
        )).one()
        with pytest.raises(IntegrityError), connection.begin_nested():
            final.downgrade()
        assert connection.execute(text(
            "SELECT * FROM shift_report_materials_unmatched_archive"
        )).one() == archived
        assert "material" not in {
            column["name"] for column in inspect(connection).get_columns("shift_report_materials")
        }


def test_failed_archive_write_rolls_back_usage_deletion(link_session, scenario):
    specification(link_session, scenario)
    connection = link_session.connection()
    final = load_migration("20261019150000_require_shift_project_material.py")
    with Operations.context(MigrationContext.configure(connection)):
        final.downgrade()
        final.upgrade()  # Create an empty archive.
        actual = add_actual(link_session, scenario, shift_report_detail=None)
        final.downgrade()
        connection.execute(text("UPDATE shift_report_materials SET project_material = NULL"))
        connection.execute(text("""
            ALTER TABLE shift_report_materials_unmatched_archive
            ADD CONSTRAINT reject_archive_write CHECK (quantity < 0)
        """))
        with pytest.raises(IntegrityError), connection.begin_nested():
            final.upgrade()
        assert str(connection.execute(text(
            "SELECT shift_report_material_id FROM shift_report_materials"
        )).scalar_one()) == actual["shift_report_material_id"]
        assert connection.execute(text(
            "SELECT count(*) FROM shift_report_materials_unmatched_archive"
        )).scalar_one() == 0
