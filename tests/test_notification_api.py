from uuid import UUID, uuid4

from app.adapters.notifications import SQLAlchemyNotificationRepository
from app.database.models import ApiKeys, KeyPermissionTypeRelations, PermissionTypes
from app.use_cases.notifications import CreateNotificationCommand, CreateNotificationUseCase
from app.utils.api_key_permissions import set_api_key_permissions


def headers(token, key=None):
    result = {"Authorization": f"Bearer {token}"}
    if key:
        result["API-Key"] = key
    return result


def create_notification(user_id):
    return CreateNotificationUseCase(SQLAlchemyNotificationRepository()).execute(
        CreateNotificationCommand(str(uuid4()), "test", "Title", "Text", (UUID(user_id),))
    )


def test_history_count_view_and_ownership(client, db_session, seed_user, seed_admin, jwt_token_user, jwt_token_admin):
    db_session.rollback()
    own = create_notification(seed_user["user_id"])
    other = create_notification(seed_admin["user_id"])
    auth = headers(jwt_token_user)
    history = client.get('/notifications?limit=1&offset=0', headers=auth)
    assert history.status_code == 200
    assert [x['notification_id'] for x in history.json['items']] == [str(own.notification_id)]
    assert 'browser_id' not in history.json['items'][0]
    assert client.get('/notifications/unread-count', headers=auth).json == {'count': 1}
    admin_before = client.get(f'/notifications/admin/users/{seed_user["user_id"]}', headers=headers(jwt_token_admin))
    assert admin_before.status_code == 200 and admin_before.json['items'][0]['viewed'] is False
    assert client.get('/notifications/unread-count', headers=auth).json == {'count': 1}
    assert client.get('/notifications?limit=0', headers=auth).status_code == 400
    assert client.post(f'/notifications/{own.notification_id}/view', headers=auth).status_code == 401
    client.set_cookie('browser_id', 'invalid')
    assert client.post(f'/notifications/{own.notification_id}/view', headers=auth).status_code == 401
    client.set_cookie('browser_id', str(uuid4()))
    assert client.post(f'/notifications/{other.notification_id}/view', headers=auth).status_code == 404
    first = client.post(f'/notifications/{own.notification_id}/view', headers=auth)
    again = client.post(f'/notifications/{own.notification_id}/view', headers=auth)
    assert first.status_code == 200 and first.json['viewed_at'] == again.json['viewed_at']
    assert client.get('/notifications/unread-count', headers=auth).json == {'count': 0}
    assert client.get(f'/notifications/admin/users/{seed_user["user_id"]}', headers=auth).status_code == 403
    admin = client.get(f'/notifications/admin/users/{seed_user["user_id"]}', headers=headers(jwt_token_admin))
    assert admin.status_code == 200 and admin.json['items'][0]['viewed'] is True
    assert 'browser_id' not in admin.json['items'][0]
    assert client.get(f'/notifications/admin/users/{uuid4()}', headers=headers(jwt_token_admin)).status_code == 404
    assert client.get('/notifications').status_code == 401


def test_api_key_is_additional_permission_not_identity(client, db_session, seed_user, jwt_token_user, jwt_token_admin):
    set_api_key_permissions()
    key = ApiKeys(name='notifications test', token='key-for-test', expires_at=None)
    db_session.add(key)
    db_session.commit()
    assert client.get('/notifications', headers={'API-Key': key.token}).status_code == 401
    assert client.get('/notifications', headers=headers(jwt_token_user, '') | {'API-Key': ''}).status_code == 403
    assert client.get('/notifications', headers=headers(jwt_token_user, key.token)).status_code == 403
    permission = db_session.query(PermissionTypes).filter_by(code='notifications-list').one()
    db_session.add(KeyPermissionTypeRelations(api_key_id=key.api_key_id, permission_type_id=permission.permission_type_id))
    admin_permission = db_session.query(PermissionTypes).filter_by(code='notifications-admin-list').one()
    db_session.add(KeyPermissionTypeRelations(api_key_id=key.api_key_id, permission_type_id=admin_permission.permission_type_id))
    db_session.commit()
    assert client.get('/notifications', headers=headers(jwt_token_user, key.token)).status_code == 200
    assert client.get(f'/notifications/admin/users/{seed_user["user_id"]}', headers=headers(jwt_token_user, key.token)).status_code == 403
    assert client.get(f'/notifications/admin/users/{seed_user["user_id"]}', headers=headers(jwt_token_admin, key.token)).status_code == 200


def test_notification_routes_reject_revoked_session(client, seed_admin):
    login = client.post('/auth/login', json={'login': 'test_admin', 'password': 'qweasdzcx'})
    assert login.status_code == 200
    auth = headers(login.json['access_token'])
    assert client.post('/auth/logout', headers=auth).status_code == 204
    assert client.get('/notifications', headers=auth).status_code == 401
    assert client.get('/notifications/push/subscriptions', headers=auth).status_code == 401
    assert client.get(f'/notifications/admin/users/{seed_admin["user_id"]}', headers=auth).status_code == 401


def test_push_device_list_and_revoke(client, seed_admin, seed_user, jwt_token_user):
    login = client.post('/auth/login', json={'login': 'test_admin', 'password': 'qweasdzcx'})
    assert login.status_code == 200
    auth = headers(login.json['access_token'])
    registered = client.put('/notifications/push/subscription', headers=auth,
                            json={'platform': 'web', 'token': 'secret-fcm-token'})
    assert registered.status_code == 200
    listed = client.get('/notifications/push/subscriptions', headers=auth)
    assert listed.status_code == 200 and len(listed.json['items']) == 1
    assert 'secret-fcm-token' not in str(listed.json)
    subscription_id = registered.json['subscription_id']
    user_auth = headers(jwt_token_user)
    assert client.get('/notifications/push/subscriptions', headers=user_auth).json['items'] == []
    assert client.delete(f'/notifications/push/subscriptions/{subscription_id}', headers=user_auth).status_code == 404
    admin_list = client.get(f'/notifications/admin/users/{seed_admin["user_id"]}/push/subscriptions', headers=auth)
    assert admin_list.status_code == 200 and len(admin_list.json['items']) == 1
    assert 'secret-fcm-token' not in str(admin_list.json)
    assert client.delete(f'/notifications/push/subscriptions/{uuid4()}', headers=auth).status_code == 404
    assert client.delete(f'/notifications/push/subscriptions/{subscription_id}', headers=auth).status_code == 204
    assert client.delete(f'/notifications/push/subscriptions/{subscription_id}', headers=auth).status_code == 204
    assert client.get('/notifications/push/subscriptions', headers=auth).json['items'][0]['active'] is False
