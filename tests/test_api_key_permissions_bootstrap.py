from app.utils.api_key_permissions import API_KEY_PERMISSIONS


def test_api_key_permission_seed_has_unique_codes_and_descriptions():
    codes = [code for code, _ in API_KEY_PERMISSIONS]
    descriptions = [description for _, description in API_KEY_PERMISSIONS]

    assert len(codes) == len(set(codes))
    assert len(descriptions) == len(set(descriptions))
    assert ("acceptances-history-list", "GET /acceptances/{acceptance_id}/history") in API_KEY_PERMISSIONS
    assert ("work-plans-list", "GET /work_plans/all") in API_KEY_PERMISSIONS


def test_bootstrap_adds_only_missing_permissions_and_is_idempotent(monkeypatch):
    from app.utils.api_key_permissions import set_api_key_permissions

    seeded_codes = {"roles-list"}

    class Query:
        def filter(self, _expression):
            return self

        def all(self):
            return [(code,) for code in seeded_codes]

    class Session:
        def query(self, _model):
            return Query()

        def add_all(self, records):
            seeded_codes.update(record.code for record in records)

        def commit(self):
            return None

        def rollback(self):
            return None

        def close(self):
            return None

    with monkeypatch.context() as patch:
        patch.setattr("app.utils.api_key_permissions.db_globals.Session", Session)
        inserted = set_api_key_permissions()
        repeated_inserted = set_api_key_permissions()

    assert inserted == len(API_KEY_PERMISSIONS) - 1
    assert repeated_inserted == 0
    assert seeded_codes == {code for code, _ in API_KEY_PERMISSIONS} | {"roles-list"}
