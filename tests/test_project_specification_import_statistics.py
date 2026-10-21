import inspect
import json
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from flask import Flask

from app.adapters.projects.specification_import_repository import (
    SQLAlchemyProjectSpecificationImportRepository,
)
from app.adapters.statistics import (
    RedisProjectMaterialStatistics,
    RedisProjectWorkStatistics,
)
from app.database import db_globals
from app.domain.project_materials import ProjectMaterial
from app.domain.project_works import ProjectWork
from app.domain.projects import ProjectNotFoundError
from app.use_cases.project_specification_import import ProjectSpecificationImportActor
from app.web.projects import routes


@pytest.fixture
def import_context(monkeypatch):
    project_id, user_id = uuid4(), uuid4()
    work = ProjectWork(
        project_work_id=uuid4(), project_work_name="Work", project=project_id,
        work=uuid4(), quantity=Decimal("2"), summ=Decimal("6"),
        price=Decimal("3"), signed=False, created_by=user_id, created_at=1,
    )
    material = ProjectMaterial(
        project_material_id=uuid4(), project=project_id, material=uuid4(),
        quantity=Decimal("4"), price=Decimal("5"), summ=Decimal("20"),
        project_work=work.project_work_id, created_by=user_id, created_at=1,
    )
    factory = MagicMock()
    transaction = factory.begin.return_value
    session = transaction.__enter__.return_value
    session.get.return_value.deleted = False
    session.query.return_value.filter.return_value.all.side_effect = [
        [], [], [(work.work,)], [(material.material,)],
    ]
    monkeypatch.setattr(db_globals, "Session", factory)
    return project_id, ProjectSpecificationImportActor(user_id, "manager"), work, material, session, transaction


@pytest.mark.parametrize("kind", ["both", "works", "materials"])
def test_import_replaces_existing_caches_after_commit(import_context, kind):
    project_id, actor, work, material, session, transaction = import_context
    committed = False

    def commit(*args):
        nonlocal committed
        committed = True
        return False

    transaction.__exit__.side_effect = commit
    if kind == "works":
        session.query.return_value.filter.return_value.all.side_effect = [[], [(work.work,)]]
    elif kind == "materials":
        session.query.return_value.filter.return_value.all.side_effect = [[], [(material.material,)]]

    redis = MagicMock()
    cache = {
        f"project-work-stats:{project_id}": '{"old": {}}',
        f"project-material-stats:{project_id}": '{"old": {}}',
    }
    redis.set.side_effect = lambda key, value: cache.__setitem__(key, value)
    source = MagicMock()
    work_stats = {str(work.work): {"project_work_quantity": 2.0}}
    material_stats = {str(material.material): {"project_material_quantity": 4.0}}

    def work_source(actual_project_id):
        assert committed
        assert actual_project_id == project_id
        return work_stats

    def material_source(actual_project_id):
        assert committed
        assert actual_project_id == project_id
        return material_stats

    source.get_project_stats.side_effect = work_source
    source.get_project_material_stats.side_effect = material_source
    repository = SQLAlchemyProjectSpecificationImportRepository(
        statistics=RedisProjectWorkStatistics(redis, source),
        material_statistics=RedisProjectMaterialStatistics(redis, source),
    )

    repository.import_specification(
        project_id, actor, [] if kind == "materials" else [work],
        [] if kind == "works" else [material],
    )

    assert json.loads(cache[f"project-work-stats:{project_id}"]) == work_stats
    assert json.loads(cache[f"project-material-stats:{project_id}"]) == material_stats
    source.get_project_stats.assert_called_once_with(project_id)
    source.get_project_material_stats.assert_called_once_with(project_id)


@pytest.mark.parametrize("failure", ["flush", "commit", "missing_project"])
def test_import_does_not_recalculate_without_changes_committed(import_context, failure):
    project_id, actor, work, material, session, transaction = import_context
    work_statistics, material_statistics = MagicMock(), MagicMock()
    repository = SQLAlchemyProjectSpecificationImportRepository(
        statistics=work_statistics, material_statistics=material_statistics,
    )
    if failure == "flush":
        session.flush.side_effect = RuntimeError("flush failed")
    elif failure == "commit":
        transaction.__exit__.side_effect = RuntimeError("commit failed")
    elif failure == "missing_project":
        session.get.return_value = None
    expected_error = ProjectNotFoundError if failure == "missing_project" else RuntimeError
    with pytest.raises(expected_error):
        repository.import_specification(project_id, actor, [work], [material])

    work_statistics.recalculate_many.assert_not_called()
    material_statistics.recalculate_many.assert_not_called()


def test_import_endpoint_wires_both_redis_statistics(monkeypatch):
    app = Flask(__name__)
    redis = MagicMock()
    app.extensions["redis"] = redis
    repository_factory = MagicMock()
    monkeypatch.setattr(routes, "SQLAlchemyProjectSpecificationImportRepository", repository_factory)
    monkeypatch.setattr(routes, "_get_current_user", lambda: {"user_id": str(uuid4()), "role": "manager"})

    with app.test_request_context(json={"project_works": [], "project_materials": []}):
        response, status = inspect.unwrap(routes.ProjectSpecificationImport.post)(
            routes.ProjectSpecificationImport(), str(uuid4()),
        )

    assert status == 200
    assert response == {"project_works_created": 0, "project_materials_created": 0}
    dependencies = repository_factory.call_args.kwargs
    assert isinstance(dependencies["statistics"], RedisProjectWorkStatistics)
    assert isinstance(dependencies["material_statistics"], RedisProjectMaterialStatistics)
    assert dependencies["statistics"].client is redis
    assert dependencies["material_statistics"].client is redis
    repository_factory.return_value.import_specification.assert_called_once()


@pytest.mark.parametrize("failed_cache", ["works", "materials", "both"])
@pytest.mark.parametrize("invalidation_fails", [False, True])
def test_failed_refresh_is_independent_and_repeat_repairs_caches(
    import_context, failed_cache, invalidation_fails, caplog,
):
    project_id, actor, work, material, session, transaction = import_context
    work_statistics, material_statistics = MagicMock(), MagicMock()
    caches = {"works": work_statistics, "materials": material_statistics}
    for name, statistics in caches.items():
        if failed_cache in (name, "both"):
            statistics.recalculate_many.side_effect = RuntimeError("refresh failed")
            if invalidation_fails:
                statistics.delete_project_stats.side_effect = RuntimeError("delete failed")
    repository = SQLAlchemyProjectSpecificationImportRepository(
        statistics=work_statistics, material_statistics=material_statistics,
    )

    repository.import_specification(project_id, actor, [work], [material])

    for name, statistics in caches.items():
        statistics.recalculate_many.assert_called_once_with({project_id})
        if failed_cache in (name, "both"):
            statistics.delete_project_stats.assert_called_once_with(project_id)
            assert f"Post-import {name} statistics refresh failed" in caplog.text
            if invalidation_fails:
                assert f"Post-import {name} statistics invalidation failed" in caplog.text
        else:
            statistics.delete_project_stats.assert_not_called()
        statistics.recalculate_many.side_effect = None
        statistics.reset_mock()

    session.reset_mock()
    session.query.return_value.filter.return_value.all.side_effect = [
        [(work.project_work_id,)], [(material.project_material_id,)],
    ]
    repository.import_specification(project_id, actor, [work], [material])

    session.add_all.assert_not_called()
    session.flush.assert_not_called()
    for statistics in caches.values():
        statistics.recalculate_many.assert_called_once_with({project_id})
        statistics.delete_project_stats.assert_not_called()


def test_repeated_import_refreshes_both_caches_after_transaction(import_context):
    project_id, actor, work, material, session, transaction = import_context
    session.query.return_value.filter.return_value.all.side_effect = [
        [(work.project_work_id,)], [(material.project_material_id,)],
    ]
    events = []
    transaction.__exit__.side_effect = lambda *args: events.append("commit") or False
    work_statistics, material_statistics = MagicMock(), MagicMock()
    work_statistics.recalculate_many.side_effect = lambda ids: events.append("works")
    material_statistics.recalculate_many.side_effect = lambda ids: events.append("materials")

    SQLAlchemyProjectSpecificationImportRepository(
        statistics=work_statistics, material_statistics=material_statistics,
    ).import_specification(project_id, actor, [work], [material])

    assert events == ["commit", "works", "materials"]
    session.add_all.assert_not_called()


@pytest.mark.parametrize("kind", ["works", "materials"])
def test_invalidated_cache_is_rebuilt_on_next_read(import_context, kind):
    project_id, actor, work, material, session, transaction = import_context
    prefix = "project-work-stats" if kind == "works" else "project-material-stats"
    key = f"{prefix}:{project_id}"
    cache = {key: '{"stale": {}}'}
    redis = MagicMock()
    redis.get.side_effect = cache.get
    redis.set.side_effect = lambda name, value: cache.__setitem__(name, value)
    redis.delete.side_effect = lambda name: cache.pop(name, None)
    source = MagicMock()
    expected = {"fresh": {"quantity": 2.0}}
    if kind == "works":
        source.get_project_stats.side_effect = [RuntimeError("DB read failed"), expected]
        statistics = RedisProjectWorkStatistics(redis, source)
        repository = SQLAlchemyProjectSpecificationImportRepository(statistics=statistics)
        read_stats = statistics.get_project_stats
    else:
        source.get_project_material_stats.side_effect = [RuntimeError("DB read failed"), expected]
        statistics = RedisProjectMaterialStatistics(redis, source)
        repository = SQLAlchemyProjectSpecificationImportRepository(material_statistics=statistics)
        read_stats = statistics.get_project_material_stats

    repository.import_specification(project_id, actor, [work], [material])

    assert key not in cache
    redis.delete.assert_called_once_with(key)
    assert read_stats(project_id) == expected
    assert json.loads(cache[key]) == expected
