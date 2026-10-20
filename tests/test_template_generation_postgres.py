"""Generation repositories and all report builders against an isolated PostgreSQL schema."""

import os
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker

from app.adapters.template_generation.data_repository import (
    MarshmallowDocumentDataSerializer,
    SQLAlchemyDocumentDataRepository,
)
from app.adapters.templates.sqlalchemy_repository import SQLAlchemyTemplateRepository
from app.database import db_globals
from app.database.db_setup import Base
from app.database.models import (
    Leaves,
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
    WorkPrices,
    Works,
)
from app.database.models.leaves import AbsenceReason
from app.domain.templates import Template, TemplateTypes
from app.use_cases.template_generation.build_data import (
    BuildDocumentData,
    period_bounds,
)
from app.use_cases.template_generation.dto import GenerationParameters


@pytest.fixture
def report_database(monkeypatch):
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    admin_engine = create_engine(url, connect_args={"connect_timeout": 3})
    schema = f"test_generation_{uuid4().hex}"
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        url, connect_args={"connect_timeout": 3, "options": f"-csearch_path={schema}"}
    )
    try:
        Base.metadata.create_all(engine)
        factory = scoped_session(sessionmaker(bind=engine))
        monkeypatch.setattr(db_globals, "Session", factory)
        with factory() as session:
            session.add(Roles(role_id="admin", name="Admin"))
            session.flush()
            user_id = uuid4()
            user = Users(
                user_id=user_id,
                login="print",
                name="Print user",
                password_hash="private",
                role="admin",
                created_by=user_id,
            )
            session.add(user)
            session.flush()
            obj = Objects(name="Object", created_by=user_id)
            work = Works(name="Work", created_by=user_id)
            material = Materials(name="Material", created_by=user_id)
            session.add_all([obj, work, material])
            session.flush()
            project = Projects(name="Project", object=obj.object_id, created_by=user_id)
            session.add(project)
            session.flush()
            position = ProjectWorks(
                project=project.project_id,
                work=work.work_id,
                quantity=10,
                price=Decimal("3.33"),
                created_by=user_id,
            )
            materials = [
                ProjectMaterials(
                    project=project.project_id,
                    material=material.material_id,
                    quantity=10,
                    price=price,
                    created_by=user_id,
                )
                for price in (Decimal("2.1"), Decimal(10))
            ]
            session.add_all(
                [
                    position,
                    *materials,
                    WorkPrices(
                        work=work.work_id, category=0, price=0, created_by=user_id
                    ),
                ]
            )
            session.flush()
            start, end = period_bounds(date(2026, 10, 5), date(2026, 10, 6))
            leave = Leaves(
                user_id=user_id,
                responsible_id=user_id,
                start_date=start,
                end_date=start + 86400000,
                reason=AbsenceReason.DAY_OFF,
                created_by=user_id,
            )
            session.add(leave)
            session.flush()
            shifts = []
            for timestamp, signed, deleted, leave_id in [
                (start, True, False, None),
                (end - 1, True, False, None),
                (start - 1, True, False, None),
                (end, True, False, None),
                (start, False, False, None),
                (start, True, True, None),
                (start, True, False, leave.leave_id),
            ]:
                row = ShiftReports(
                    user=user_id,
                    project=project.project_id,
                    date=timestamp,
                    signed=signed,
                    deleted=deleted,
                    leave_id=leave_id,
                    created_by=user_id,
                )
                session.add(row)
                session.flush()
                session.add(
                    ShiftReportDetails(
                        shift_report=row.shift_report_id,
                        project_work=position.project_work_id,
                        work=work.work_id,
                        quantity=Decimal("2.5"),
                        summ=999,
                        created_by=user_id,
                    )
                )
                for mat in materials:
                    session.add(
                        ShiftReportMaterials(
                            shift_report=row.shift_report_id,
                            project_material=mat.project_material_id,
                            quantity=3,
                            created_by=user_id,
                        )
                    )
                shifts.append(row.shift_report_id)
            session.commit()
            context = {
                "user": user_id,
                "project": project.project_id,
                "work": work.work_id,
                "shifts": shifts,
                "leave": leave.leave_id,
            }
        yield context, factory
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def parameters(**kwargs):
    return GenerationParameters(
        date_from=date(2026, 10, 5), date_to=date(2026, 10, 6), **kwargs
    )


def test_all_five_builders_and_database_selection(report_database):
    context, _factory = report_database
    repository = SQLAlchemyDocumentDataRepository()
    builder = BuildDocumentData(repository, MarshmallowDocumentDataSerializer())
    registry = builder.execute(TemplateTypes.SHIFT_REPORT_LIST, parameters())[
        "shift_reports"
    ]
    assert [row["shift_report_id"] for row in registry] == [
        str(row) for row in context["shifts"][:2]
    ]
    assert all(
        row["signed"] and not row["deleted"] and row["leave_id"] is None
        for row in registry
    )
    assert all(
        row["shift_report_details_summ_by_estimate"] == 8.325 for row in registry
    )
    assert "password_hash" not in registry[0]["user"]
    single = builder.execute(
        TemplateTypes.SHIFT_REPORT,
        GenerationParameters(shift_report_id=context["shifts"][0]),
    )["shift_report"]
    assert len(single["shift_report_materials"]) == 2
    assert single["shift_report_details"][0]["work"]["work_prices"][0]["category"] == 0
    assert single["shift_report_details"][0]["work"]["work_prices"][0]["price"] == 0
    payroll = builder.execute(TemplateTypes.PAYROLL, parameters(user=context["user"]))
    assert payroll["total_summ"] == 16.65
    assert [len(row["leave"]) for row in payroll["data"]] == [1, 1]
    objects = builder.execute(
        TemplateTypes.OBJECT_REPORT,
        parameters(users=(context["user"],), projects=(context["project"],)),
    )
    project = objects["objects"][0]["projects"][0]
    assert project["works"][0]["quantity"] == 5
    assert project["works"][0]["summ"] == 16.65
    assert project["materials"][0]["quantity"] == 12
    assert project["materials"][0]["summ"] == 72.6
    assert builder.execute(TemplateTypes.WORK_TYPES, GenerationParameters())["works"][
        0
    ]["work_id"] == str(context["work"])
    assert (
        builder.execute(TemplateTypes.SHIFT_REPORT_LIST, parameters(users=(uuid4(),)))[
            "shift_reports"
        ]
        == []
    )
    with pytest.raises(ValueError, match="Не найдены"):
        builder.execute(TemplateTypes.PAYROLL, parameters(user=uuid4()))
    with pytest.raises(ValueError, match="Не найдены"):
        builder.execute(TemplateTypes.OBJECT_REPORT, parameters(projects=(uuid4(),)))
    for identifier in context["shifts"][4:]:
        with pytest.raises(ValueError, match="недоступна"):
            builder.execute(
                TemplateTypes.SHIFT_REPORT,
                GenerationParameters(shift_report_id=identifier),
            )


def test_default_template_repository_lookup(report_database):
    repository = SQLAlchemyTemplateRepository()
    assert repository.get_default(TemplateTypes.WORK_TYPES) is None
    template = Template(
        id=uuid4(),
        name="Template",
        template_type=TemplateTypes.WORK_TYPES,
        s3_key="key",
        file_name="template.docx",
        content_type="application/docx",
        is_default=True,
    )
    repository.create(template)
    assert repository.get_default(TemplateTypes.WORK_TYPES) == template
    assert repository.get_default(TemplateTypes.PAYROLL) is None
