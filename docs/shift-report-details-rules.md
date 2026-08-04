# Правила расчёта `shift_report_details`

Документ фиксирует контракт дополнительных полей в ответах:

- `GET /shift_report_details/all`;
- `POST /shift_report_details/all-by-reports`.
- `GET /project_works/{project_work_id}/view` возвращает те же два значения статистики.

## Исходный метод статистики

Основой для этих расчётов является `GET /projects/{project_id}/get-stat`.
Он возвращает объект `stats`, сгруппированный по `work_id`:

```json
{
  "work_id": {
    "project_work_quantity": 10,
    "shift_report_details_quantity": 6,
    "project_work_name": "Название работы"
  }
}
```

Метод собирает план из `project_works`, а факт — из `shift_report_details`,
относящихся к согласованным сменным отчётам проекта (`signed = true`).
И план, и факт суммируются по `work`, поэтому это поведение является источником
истины для статистики, добавляемой в ответы `shift_report_details`.

## Статистика `project_work`

Если у детали заполнен `project_work`, вложенный объект содержит:

```json
{
  "project_work_id": "uuid",
  "name": "Название работы",
  "project_work_quantity": 10,
  "shift_report_details_quantity": 6,
  "acceptance_status": "partial"
}
```

Расчёт выполняется по тому же правилу, что и `get_project_stats`:

1. `project_work_quantity` — сумма плановых `quantity` из `project_works` проекта.
2. `shift_report_details_quantity` — сумма `quantity` из деталей сменных отчётов проекта.
3. Учитываются только детали отчётов, у которых `signed = true`.
4. Группировка выполняется по `work`, а не по `project_work_id`. Поэтому одинаковая работа в нескольких `project_work` учитывается общей суммой.

## `acceptance_status`

Статус вычисляется по фактическому и плановому количеству:

| Условие | Статус |
| --- | --- |
| `shift_report_details_quantity == 0` | `not_checked` |
| `0 < shift_report_details_quantity < project_work_quantity` | `partial` |
| `shift_report_details_quantity >= project_work_quantity` | `accepted` |

Если `project_work` у детали равен `null`, вложенный объект остаётся `null`, а дополнительные поля статистики не добавляются.

Эти поля являются response-only: клиент не передаёт их при создании или редактировании деталей.

## Управление расчётом статистики

Методы `GET /shift_report_details/all` и `POST /shift_report_details/all-by-reports`
принимают параметр `with_stat` типа `bool`. При `with_stat=true` для деталей с
заполненным `project_work` вычисляются и возвращаются `project_work_quantity`,
`shift_report_details_quantity` и `acceptance_status`. При `with_stat=false` или
если параметр не передан, эти поля не вычисляются и не возвращаются.

## Фиксация времени смены

Время смены фиксируется отдельными endpoint’ами:

- `PATCH /shift_reports/{shift_report_id}/start` — принимает `lng` и `ltd`, записывает `date_start`, `lng_start`, `ltd_start`;
- `PATCH /shift_reports/{shift_report_id}/finish` — принимает `lng` и `ltd`, записывает `date_end`, `lng_end`, `ltd_end`.

Время записывается как Unix timestamp в миллисекундах через `utc_epoch_milliseconds()`. Это абсолютный момент времени; при отображении его следует интерпретировать в часовом поясе `Asia/Novosibirsk`.

Повторный `start`, `finish` до `start` и повторный `finish` возвращают `409`. Координаты должны присутствовать и быть числами; ошибки входных данных возвращают `400`. Основной `PATCH /shift_reports/{shift_report_id}/edit` также принимает `date_start`, `date_end`, `lng_start`, `ltd_start`, `lng_end` и `ltd_end` для ручного исправления.

## Создание сменного отчёта

`POST /shift_reports/add` доступен всем ролям, кроме `user`. Роль `user` получает `403` и не может создать сменный отчёт.

Поле `user` определяет пользователя, на которого оформляется смена, а `created_by` всегда заполняется из текущего JWT/API key пользователя.
