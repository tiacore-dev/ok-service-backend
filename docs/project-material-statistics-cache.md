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
   умноженное на цену строки `project_materials`, соответствующей цепочке
   `shift_report_material.shift_report_detail -> project_work`. Если детали
   смены или соответствующей строки спецификации нет, количество учитывается,
   а сметная сумма равна нулю.

При нескольких строках `project_materials` для одной пары
`(project_work, material)` цена определяется как `sum(summ) / sum(quantity)`.
Это не допускает размножения фактического количества при SQL join.

При cache miss агрегат рассчитывается из PostgreSQL и сохраняется в Redis. При
временной недоступности Redis API возвращает расчёт из БД.

GitHub Actions прогревает весь кэш после применения миграций и перезапуска
backend-контейнера. При ошибке прогрева deployment завершается неуспешно.

Пересчёт выполняется после создания, изменения или удаления `project_works`,
`project_materials`, `shift_reports` и `shift_report_materials`. При удалении
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
