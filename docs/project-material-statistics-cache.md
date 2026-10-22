# Redis-кэш статистики материалов проекта

Статистика материалов хранится отдельно от статистики работ. Ключ Redis имеет
вид `project-material-stats:{project_id}`; верхний ключ JSON — `material_id`.
TTL не используется: актуальность обеспечивается пересчётом после изменения
исходных данных.

Для пары `(project_id, material_id)` сохраняются:

1. `project_material_quantity` — сумма `project_materials.quantity`;
2. `project_material_summ` — сумма сохранённых `project_materials.summ`;
3. `shift_report_material_quantity` — сумма `shift_report_materials.quantity`
   из подписанных и неудалённых смен проекта;
4. `shift_report_material_summ_by_estimate` — фактическое количество,
   умноженное на текущую цену конкретной строки `project_materials`, указанной
   в `shift_report_material.project_material`. Если цены нет,
   количество учитывается, а сметная сумма равна нулю.

Цена больше не усредняется между строками спецификации. Прямой join по
`project_material_id` не размножает фактическое количество. То же правило
действует для помесячной статистики прорабов. Правила выбора строки описаны
в [shift-report-materials-rules.md](./shift-report-materials-rules.md).

При cache miss агрегат рассчитывается из PostgreSQL и сохраняется в Redis. При
временной недоступности Redis API возвращает расчёт из БД.

GitHub Actions прогревает весь кэш после применения миграций и перезапуска
backend-контейнера. При ошибке прогрева deployment завершается неуспешно.

Пересчёт выполняется после создания, изменения или удаления `project_works`,
`project_materials`, `shift_reports` и `shift_report_materials`.
Атомарный импорт `POST /projects/{project_id}/import-works-and-materials`
пересчитывает кэши работ и материалов после commit общей транзакции;
при откате пересчёта нет. Повтор уже выполненного импорта запускает оба
пересчёта без повторной записи строк. Ошибка одного кэша не блокирует другой:
при исключении пересчёта выполняется удаление его ключа, чтобы следующее
чтение восстановило кэш из БД. Ошибки пересчёта и удаления логируются, импорт
остаётся успешным; повтор импорта служит дополнительным путём восстановления.
При удалении
проекта ключ материалов удаляется вместе с ключом работ. Первичное заполнение:

```bash
flask --app app:create_app rebuild-project-material-statistics
```

## API

Отдельного `GET /projects/{project_id}/get-stat-by-project-materials` нет.
Материалы возвращаются в существующих статистических API в поле
`material_stats` рядом с `stats`; агрегат материалов для `total` возвращается
в `material_totals`. В помесячном `GET /project-leaders/get-stat` возвращаются
только фактические `shift_report_material_quantity` и
`shift_report_material_summ_by_estimate`.
