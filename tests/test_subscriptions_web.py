def _auth_headers(jwt_token):
    return {"Authorization": f"Bearer {jwt_token}"}


def test_legacy_subscription_routes_are_disabled(client, jwt_token):
    headers = _auth_headers(jwt_token)
    for method, path in [
        ("POST", "/subscriptions/subscribe"),
        ("GET", "/subscriptions/all"),
        ("POST", "/subscriptions/send_notification"),
        ("DELETE", "/subscriptions/00000000-0000-0000-0000-000000000000/unsubscribe"),
    ]:
        response = client.open(path, method=method, headers=headers)
        assert response.status_code == 404
