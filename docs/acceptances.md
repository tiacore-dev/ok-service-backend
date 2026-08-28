# Приёмки работ

## Назначение

Приёмка фиксирует предъявление заказчику работ в рамках проекта. В текущей
модели проекта `project` является спецификацией, поэтому `acceptances.project_id`
ссылается на `projects.project_id`.

Приёмка хранит дату, статус и комментарий. Состав предъявленных работ хранится
отдельно в `work_acceptance_relations`.

Расчёт прогресса работ и вложения в этот срез не входят и будут добавлены
отдельно.

## Модель данных

### `acceptances`

| Поле | Тип | Описание |
| --- | --- | --- |
| `id` | UUID | Первичный ключ |
| `date` | BIGINT | Unix timestamp в миллисекундах |
| `project_id` | UUID | Проект/спецификация, внешний ключ на `projects` |
| `status` | string | Статус приёмки |
| `comment` | string, nullable | Комментарий |

Удаление проекта каскадно удаляет его приёмки.

### `work_acceptance_relations`

| Поле | Тип | Описание |
| --- | --- | --- |
| `id` | UUID | Первичный ключ |
| `acceptance_id` | UUID | Внешний ключ на `acceptances.id` |
| `work_id` | UUID | Внешний ключ на `works.work_id` |
| `quantity` | NUMERIC(10, 2) | Положительное количество предъявленной работы |

Удаление приёмки каскадно удаляет её связи с работами. Уникальность пары
`acceptance_id`/`work_id` и ограничение общей предъявленной величины пока не
вводятся.

## Статусы

Используется enum `AcceptanceStatus`:

| Значение API/БД | Назначение |
| --- | --- |
| `presented` | Предъявлено |
| `violations_found` | Выявлены нарушения |
| `accepted_on_site` | Принято на объекте |
| `documents_signed` | Документы подписаны |

Переходы между статусами пока не ограничиваются: приёмку можно редактировать и
переводить в любой статус из enum.

## Права доступа

Все маршруты требуют `api_key_or_jwt_required`.

- просмотр и списки доступны аутентифицированным пользователям;
- создание, редактирование и удаление приёмок доступны `admin` и `manager`;
- создание, редактирование и удаление связей с работами также доступны только
  `admin` и `manager`.

Отдельной роли инженера ПТО в этом срезе не вводилось. Права можно будет
изменить позднее без изменения структуры таблиц.

## API приёмок

### Создание

`POST /acceptances/add`

```json
{
  "date": 1754006400000,
  "project_id": "project-uuid",
  "status": "presented",
  "comment": "Работы предъявлены заказчику"
}
```

`status` и `date` обязательны. `comment` необязателен.

Успешный ответ содержит `msg` и созданный `id`:

```json
{
  "msg": "Acceptance added successfully",
  "id": "acceptance-uuid"
}
```

### Получение одной записи

`GET /acceptances/{id}/view`

Ответ содержит объект `acceptance` с полями `id`, `date`, `project_id`, `status`
и `comment`.

### Редактирование

`PATCH /acceptances/{id}/edit`

Принимает частичный JSON с полями `date`, `project_id`, `status`, `comment`.
Передача `comment: null` очищает комментарий. Пустое тело не изменяет запись,
но проходит обычную проверку существования приёмки.

### Удаление

`DELETE /acceptances/{id}/delete/hard`

Удаляет приёмку и связанные с ней строки. При наличии других ограничений БД
возвращается конфликт `409`.

### Список

`GET /acceptances/all`

Поддерживаются параметры:

- `offset` — смещение, по умолчанию `0`;
- `limit` — размер страницы, по умолчанию `1000`;
- `project_id` — фильтр по проекту;
- `status` — фильтр по enum-статусу.

## API связей с работами

Маршруты используют namespace `/work-acceptance-relations` и тот же CRUD-стиль:

| Операция | Метод и маршрут |
| --- | --- |
| Создание | `POST /work-acceptance-relations/add` |
| Просмотр | `GET /work-acceptance-relations/{id}/view` |
| Редактирование | `PATCH /work-acceptance-relations/{id}/edit` |
| Удаление | `DELETE /work-acceptance-relations/{id}/delete/hard` |
| Список | `GET /work-acceptance-relations/all` |

Создание принимает:

```json
{
  "acceptance_id": "acceptance-uuid",
  "work_id": "work-uuid",
  "quantity": 12.5
}
```

`quantity` должен быть строго больше нуля. Список поддерживает фильтры
`acceptance_id`, `work_id`, `offset` и `limit`.

## Архитектура реализации

Фича разделена на слои:

- `app/domain/acceptances` и `app/domain/work_acceptance_relations` — сущности,
  enum и доменные проверки;
- `app/use_cases/acceptances` и `app/use_cases/work_acceptance_relations` — CRUD
  сценарии и repository Protocol;
- `app/adapters/acceptances` и `app/adapters/work_acceptance_relations` — SQLAlchemy
  repositories поверх существующего manager-слоя;
- `app/web/acceptances` и `app/web/work_acceptance_relations` — Flask-RESTX
  namespace, Marshmallow validation, Swagger-модели и преобразование ошибок.

Таблицы добавляются миграцией
`alembic/versions/20260827150000_acceptances.py`.

## Тестирование

Добавлен `tests/test_acceptances.py`. Он проверяет:

- нормализацию статуса и timestamp;
- запрет нулевого количества в relation;
- разрешение mutation для `manager`;
- запрет mutation для `project-leader`.

Будущие изменения прав, вложений, переходов статусов и прогресса должны
дополняться отдельными тестами API и use-case.
