"""Integration checks in an isolated schema of TEST_DATABASE_URL."""

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.adapters.templates.s3_storage import S3TemplateStorage
from app.adapters.templates.sqlalchemy_repository import SQLAlchemyTemplateRepository
from app.database import db_globals
from app.domain.templates import (
    Template,
    TemplateConflictError,
    TemplateNotFoundError,
    TemplateTypes,
)
from app.use_cases.templates.manage_templates import TemplateUseCase
from tests.test_stored_templates import FakeS3Manager, office_file


@pytest.fixture
def postgres(monkeypatch):
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    engine = create_engine(url, connect_args={"connect_timeout": 3})
    schema = f"test_templates_{uuid4().hex}"
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    isolated = create_engine(
        url, connect_args={"connect_timeout": 3, "options": f"-csearch_path={schema}"}
    )
    path = Path(__file__).parents[1] / "alembic/versions/20261019120000_templates.py"
    spec = spec_from_file_location("templates_pg_migration", path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    codes_path = path.with_name("20261019130000_template_type_codes.py")
    codes_spec = spec_from_file_location("template_codes_pg_migration", codes_path)
    assert codes_spec is not None and codes_spec.loader is not None
    codes_migration = module_from_spec(codes_spec)
    codes_spec.loader.exec_module(codes_migration)
    try:
        with (
            isolated.begin() as connection,
            Operations.context(MigrationContext.configure(connection)),
        ):
            migration.upgrade()
            codes_migration.upgrade()
        with monkeypatch.context() as patch:
            patch.setattr(db_globals, "Session", sessionmaker(bind=isolated))
            yield SQLAlchemyTemplateRepository(), isolated, migration, codes_migration
    finally:
        isolated.dispose()
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def template(**changes):
    return Template(
        id=uuid4(),
        name="Test",
        template_type=TemplateTypes.WORK_TYPES,
        s3_key=str(uuid4()),
        file_name="test.docx",
        content_type="application/octet-stream",
        **changes,
    )


def test_postgres_migration_crud_defaults_and_downgrade(postgres):
    repository, engine, migration, codes_migration = postgres
    item = template(is_default=True, description="text")
    repository.create(item)
    assert repository.get(item.id) == item
    with pytest.raises(TemplateConflictError):
        repository.create(template(is_default=True))
    other_type = replace(template(is_default=True), template_type=TemplateTypes.PAYROLL)
    repository.create(other_type)
    candidate = template()
    repository.create(candidate)
    with pytest.raises(TemplateConflictError):
        repository.update(candidate.id, {"is_default": True})
    assert repository.get(candidate.id) == candidate
    updated, old_key = repository.update(
        item.id, {"description": None, "is_default": False}
    )
    assert updated.description is None and not updated.is_default and old_key is None
    assert repository.update(candidate.id, {"is_default": True})[0].is_default
    replacement, old_key = repository.update(
        item.id, {"s3_key": "new", "file_name": "new.xlsx"}
    )
    assert old_key == item.s3_key and replacement.file_name == "new.xlsx"
    assert len(repository.list(TemplateTypes.WORK_TYPES, 0, 100)) == 2
    assert repository.list(TemplateTypes.PAYROLL, 0, 1) == [other_type]
    repository.delete(item.id)
    with pytest.raises(TemplateNotFoundError):
        repository.get(item.id)
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            codes_migration.downgrade()
            migration.downgrade()
        assert "templates" not in inspect(connection).get_table_names()
        assert not connection.execute(
            text(
                "SELECT 1 FROM pg_type WHERE typname='template_types' AND typnamespace=current_schema()::regnamespace"
            )
        ).first()


def test_postgres_concurrent_default_creation(postgres):
    repository, _, _, _ = postgres

    def create_default(_):
        try:
            repository.create(template(is_default=True))
            return "created"
        except TemplateConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(create_default, range(2))) == ["conflict", "created"]
    assert len(repository.list(None, 0, 100)) == 1


def test_postgres_concurrent_file_replacement(postgres):
    repository, _, _, _ = postgres
    manager = FakeS3Manager()
    use_case = TemplateUseCase(repository, S3TemplateStorage(manager))
    original = use_case.create(
        TemplateTypes.WORK_TYPES, "Template", {}, office_file(), "test.docx", None
    )

    def replace_file(index):
        return use_case.update(
            original.id, {}, (office_file(), f"replacement-{index}.docx", None)
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        replacements = list(pool.map(replace_file, range(2)))
    current = repository.get(original.id)
    assert current in replacements
    assert list(manager.objects) == [current.s3_key]
    assert use_case.download(original.id)[0] == office_file()


def test_type_code_migration_preserves_rows_and_default_constraint(postgres):
    repository, engine, _, codes_migration = postgres
    items = [
        replace(template(is_default=True), template_type=value)
        for value in TemplateTypes
    ]
    for item in items:
        repository.create(item)
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            codes_migration.downgrade()
        rows = dict(
            connection.execute(
                text("SELECT id, template_type::text FROM templates")
            ).all()
        )
        assert rows == {item.id: item.template_type.label() for item in items}
    # A fresh connection avoids cached enum metadata across ALTER TYPE.
    with (
        engine.begin() as connection,
        Operations.context(MigrationContext.configure(connection)),
    ):
        codes_migration.upgrade()
    for item in items:
        assert repository.get(item.id) == item
    with pytest.raises(TemplateConflictError):
        repository.create(template(is_default=True))
