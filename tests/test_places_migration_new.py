from pathlib import Path


def test_places_migration_declares_expected_revision_and_columns():
    migration = Path("alembic/versions/20260811_places.py").read_text()

    assert 'revision: str = "20260811_places"' in migration
    assert 'down_revision: Union[str, None] = "20260805_roles_list_permission"' in migration
    assert 'op.create_table(\n        "places"' in migration
    for column in ('"place_id"', '"object_id"', '"name"', '"description"', '"deleted"'):
        assert f'sa.Column({column}' in migration
    assert 'sa.ForeignKeyConstraint(["object_id"], ["objects.object_id"])' in migration
