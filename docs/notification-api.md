# API уведомлений и push-подписок

Все операции требуют access JWT с действующей серверной сессией. Если передан
`API-Key`, он дополнительно проверяется на разрешение конкретного маршрута;
ключ сам по себе не задаёт пользователя и не заменяет роль администратора.
Разрешения добавляются в каталог при запуске и не назначаются существующим ключам.
Временные значения — Unix epoch в миллисекундах.

| Метод и путь | Разрешение API-ключа | Доступ |
|---|---|---|
| GET /notifications | notifications-list | свои уведомления |
| GET /notifications/unread-count | notifications-unread-count | свои уведомления |
| POST /notifications/{notification_id}/view | notifications-view | только получатель |
| GET /notifications/push/subscriptions | notifications-push-list | свои устройства |
| PUT /notifications/push/subscription | notifications-push-register | текущий браузер и сессия |
| DELETE /notifications/push/subscriptions/{subscription_id} | notifications-push-revoke | владелец подписки |
| GET /notifications/admin/users/{user_id} | notifications-admin-list | JWT администратора |
| GET /notifications/admin/users/{user_id}/push/subscriptions | notifications-admin-push-list | JWT администратора |

Списки принимают `offset` (по умолчанию 0, неотрицательный) и `limit` (по
умолчанию 50, от 1 до 100), возвращают `{items: [...], offset, limit}`.
История сортируется по времени создания и ID по убыванию. Устройство содержит
`subscription_id`, `platform`, `active`, `created_at`, `updated_at`, `revoked_at`;
включены и отозванные подписки. Токен FCM и browser_id не возвращаются.

Элемент истории содержит `notification_id`, `notification_type`, `title`, `text`,
`created_at`, `link`, `related_entity_type`, `related_entity_id`, `viewed`,
`viewed_at`; необязательные значения могут быть null. Чтение не меняет состояние.
Счётчик возвращает `{count: integer}`. POST просмотра без тела требует корректный
cookie browser_id и возвращает `{notification_id, viewed, viewed_at}`. Повтор
сохраняет время первого просмотра. Чужое уведомление возвращает 404.

PUT регистрации принимает JSON `{platform: "web", token: "<FCM token>"}` и
требует существующий cookie browser_id, привязанный к JWT-сессии. Успех 200:
`{subscription_id, platform, active, created_at, updated_at}`. DELETE без тела
возвращает 204, повторный отзыв своей записи также 204; чужая или отсутствующая
запись — 404. Отзыв мягкий. JWT, cookie и FCM token не следует передавать в логи.

Некорректная пагинация или тело дают 400; отсутствующий, недействительный или
отозванный JWT — 401; отсутствующий или некорректный browser_id там, где он
требуется, — 401; недействительный или не имеющий разрешения API-ключ и обычный
пользователь на административном маршруте — 403. Несуществующий пользователь
административного запроса — 404. Недоступность проверки сессии или регистрации
подписки возвращает 503. UUID в пути должен иметь корректный формат; иначе 404.
