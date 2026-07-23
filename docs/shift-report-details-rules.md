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
