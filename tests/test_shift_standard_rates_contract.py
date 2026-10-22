import json
from dataclasses import asdict
from importlib.util import module_from_spec, spec_from_file_location
from io import StringIO
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from flask_restx import Api
from marshmallow import ValidationError

from app.adapters.shift_standards import SQLAlchemyShiftStandardRepository
from app.database.models import ShiftStandards
from app.domain.shift_standards import ShiftStandard
from app.schemas.shift_standard_schemas import ShiftStandardCreateSchema, ShiftStandardEditSchema
from app.web.shift_standards import routes


@pytest.fixture
def rates_web(monkeypatch):
    app = Flask(__name__)
    app.config.update(TESTING=True, JWT_SECRET_KEY="test-secret-key-with-at-least-32-bytes")
    JWTManager(app)
    Api(app).add_namespace(routes.shift_standard_ns)
    repository = Mock(spec=SQLAlchemyShiftStandardRepository)
    repository.create_shift_standard.side_effect = lambda item: item
    repository.update_shift_standard.side_effect = lambda item: item
    repository.get_shift_standard.return_value = ShiftStandard(
        uuid4(), 1, 8, None, 1, uuid4(), 1500.25, 25.5
    )
    repository.list_shift_standards.return_value = [repository.get_shift_standard.return_value]
    monkeypatch.setattr(routes, "SQLAlchemyShiftStandardRepository", lambda: repository)
    with app.app_context():
        token = create_access_token(identity=json.dumps({"user_id": str(uuid4()), "role": "admin"}))
    return app.test_client(), repository, {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("schema", [ShiftStandardCreateSchema, ShiftStandardEditSchema])
@pytest.mark.parametrize("name", ["production_rate_rub", "penalty_rate_percent"])
@pytest.mark.parametrize("value", [-1, "invalid", float("inf"), float("-inf"), float("nan")])
def test_rate_schema_validation(schema, name, value):
    with pytest.raises(ValidationError):
        schema().load({"category": 1, "standard": 8, name: value})


@pytest.mark.parametrize("method", ["post", "patch"])
@pytest.mark.parametrize("name,value", [
    ("production_rate_rub", -0.1), ("production_rate_rub", "invalid"),
    ("production_rate_rub", float("inf")), ("penalty_rate_percent", -0.1),
    ("penalty_rate_percent", 100.01), ("penalty_rate_percent", float("nan")),
])
def test_http_rejects_invalid_rates(rates_web, method, name, value):
    client, repository, headers = rates_web
    path = "/shift_standards/add" if method == "post" else f"/shift_standards/{uuid4()}/edit"
    response = getattr(client, method)(path, json={"category": 1, "standard": 8, name: value}, headers=headers)
    assert response.status_code == 400
    repository.create_shift_standard.assert_not_called()
    repository.update_shift_standard.assert_not_called()


@pytest.mark.parametrize("rates", [{}, {"production_rate_rub": None, "penalty_rate_percent": None},
                                   {"production_rate_rub": 0, "penalty_rate_percent": 0},
                                   {"production_rate_rub": 1500.25, "penalty_rate_percent": 100}])
def test_http_create_optional_rates(rates_web, rates):
    client, repository, headers = rates_web
    response = client.post("/shift_standards/add", json={"category": 1, "standard": 8, **rates}, headers=headers)
    assert response.status_code == 200
    item = repository.create_shift_standard.call_args.args[0]
    assert item.production_rate_rub == rates.get("production_rate_rub")
    assert item.penalty_rate_percent == rates.get("penalty_rate_percent")


def test_http_patch_preserves_zero_and_explicit_null(rates_web):
    client, repository, headers = rates_web
    item = repository.get_shift_standard.return_value
    path = f"/shift_standards/{item.shift_standard_id}/edit"
    for payload, production, penalty in [
        ({"standard": 9}, 1500.25, 25.5),
        ({"production_rate_rub": 0}, 0, 25.5),
        ({"penalty_rate_percent": 100}, 1500.25, 100),
        ({"production_rate_rub": None}, None, 25.5),
        ({"penalty_rate_percent": None}, 1500.25, None),
    ]:
        assert client.patch(path, json=payload, headers=headers).status_code == 200
        updated = repository.update_shift_standard.call_args.args[0]
        assert updated.production_rate_rub == production
        assert updated.penalty_rate_percent == penalty


@pytest.mark.parametrize("production,penalty", [(None, None), (0, 0), (125.5, 100)])
def test_http_read_rates_and_swagger(rates_web, production, penalty):
    client, repository, headers = rates_web
    item = repository.get_shift_standard.return_value.with_updates(
        production_rate_rub=production, penalty_rate_percent=penalty
    )
    repository.get_shift_standard.return_value = item
    repository.list_shift_standards.return_value = [item]
    viewed = client.get(f"/shift_standards/{item.shift_standard_id}/view", headers=headers)
    listed = client.get("/shift_standards/all", headers=headers)
    assert viewed.status_code == listed.status_code == 200
    for data in (viewed.json["shift_standard"], listed.json["shift_standards"][0]):
        assert data["production_rate_rub"] == production
        assert data["penalty_rate_percent"] == penalty
    definitions = client.get("/swagger.json").json["definitions"]
    for model in ("ShiftStandardCreate", "ShiftStandardEdit", "ShiftStandard"):
        for name in ("production_rate_rub", "penalty_rate_percent"):
            assert definitions[model]["properties"][name]["type"] == "number"
            assert name not in definitions[model].get("required", [])


@pytest.mark.parametrize("role,status", [(None, 401), ("user", 403)])
@pytest.mark.parametrize("method", ["post", "patch"])
def test_rate_mutations_keep_access_restrictions(rates_web, role, status, method):
    client, repository, _ = rates_web
    headers = {}
    if role:
        with client.application.app_context():
            token = create_access_token(identity=json.dumps({"user_id": str(uuid4()), "role": role}))
        headers = {"Authorization": f"Bearer {token}"}
    path = "/shift_standards/add" if method == "post" else f"/shift_standards/{uuid4()}/edit"
    response = getattr(client, method)(path, json={"category": 1, "standard": 8, "production_rate_rub": 0}, headers=headers)
    assert response.status_code == status
    repository.create_shift_standard.assert_not_called()
    repository.update_shift_standard.assert_not_called()


def test_repository_passes_rates_to_storage_and_reads_nulls():
    item = ShiftStandard(uuid4(), 1, 8, None, 1, uuid4(), 0, 100)
    manager = Mock()
    manager.add.side_effect = lambda **data: data
    manager.update_shift_standard.side_effect = lambda item_id, **data: {**asdict(item), **data}
    repository = SQLAlchemyShiftStandardRepository(manager=manager)
    assert repository.create_shift_standard(item) == item
    manager.add.assert_called_once_with(**asdict(item))
    cleared = item.with_updates(production_rate_rub=None, penalty_rate_percent=None)
    assert repository.update_shift_standard(cleared) == cleared
    assert manager.update_shift_standard.call_args.kwargs["production_rate_rub"] is None
    assert manager.update_shift_standard.call_args.kwargs["penalty_rate_percent"] is None
    manager.get_by_id.return_value = asdict(cleared)
    assert repository.get_shift_standard(item.shift_standard_id) == cleared
    orm = ShiftStandards(**asdict(cleared))
    assert orm.to_dict()["production_rate_rub"] is None
    assert orm.to_dict()["penalty_rate_percent"] is None


def test_rates_migration_adds_nullable_columns_without_backfill_and_downgrades():
    path = Path(__file__).parents[1] / "alembic/versions/20261021120000_shift_standard_rates.py"
    spec = spec_from_file_location("shift_rates_migration", path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.down_revision == "20261019150000"
    output = StringIO()
    context = MigrationContext.configure(dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output})
    with Operations.context(context):
        migration.upgrade()
    sql = output.getvalue()
    for name in ("production_rate_rub", "penalty_rate_percent"):
        assert f"ADD COLUMN {name} FLOAT" in sql
    assert "NOT NULL" not in sql
    assert "DEFAULT" not in sql
    assert "UPDATE" not in sql
    assert "CHECK (production_rate_rub >= 0 AND production_rate_rub < 'Infinity'::double precision)" in sql
    assert "CHECK (penalty_rate_percent >= 0 AND penalty_rate_percent <= 100)" in sql
    output.truncate(0)
    output.seek(0)
    with Operations.context(context):
        migration.downgrade()
    assert "DROP COLUMN penalty_rate_percent" in output.getvalue()
    assert "DROP COLUMN production_rate_rub" in output.getvalue()
