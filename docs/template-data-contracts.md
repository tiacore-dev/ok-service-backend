# Данные шаблонов по типам

## Статус

Контракт согласован в обсуждении 19–20.10.2026. Схемы находятся в
`app/schemas/template_data_schemas.py`; `TEMPLATE_DATA_SCHEMAS` связывает пять
значений `TemplateTypes` с отдельными Marshmallow-схемами. Функция
`template_data_schema(template_type)` возвращает новый экземпляр схемы.
Неизвестный тип отклоняется с `ValueError`.

Этот этап добавляет схемы параметров и `document_data`, но не выборки из БД,
сборщики отчётов, расчёты, HTTP-эндпоинт параметров или вызовы template-service.
Правила сборки ниже — основание для следующего этапа, а не уже работающий
механизм выгрузки. Действующие API остаются прежними.

Изучены модели `works`, `shift_reports`, `shift_report_details`,
`shift_report_materials`, `project_works`, `project_materials`, `leaves`,
реестр `GET /shift_reports/all` и текущий расчёт `by_estimate`.
Связь материала смены соответствует актуальному
[контракту расхода](./shift-report-materials-rules.md): обязательный
`project_material`, материал каталога доступен через эту строку спецификации.

## Общие правила формата

- Это отдельные печатные схемы: сущности раскрываются в объекты для шаблона,
  а не копируются из ORM `to_dict()` вместе со всеми полями.
- UUID сериализуются в строки; денежные значения и количества — JSON numbers.
  На этапе расчётов нужен Decimal, преобразование в число происходит на границе
  сериализации. Дополнительного округления до двух знаков схемы не вводят.
- Исходные timestamp-поля смен и отсутствий сохраняются как Unix milliseconds.
  `date_from`, `date_to` и `data[i].date` — календарные даты `YYYY-MM-DD`.
  День определяется в `Asia/Novosibirsk`; границы периода включительны.
- Поля схемы обязательны, nullable-поля явно допускают `null`. Пустые коллекции
  передаются как `[]`. Исключение — необязательные фильтры входного запроса.
- У полей есть русские `title` и обезличенные `example` в `metadata`.
  Это основа последующего построения справочника параметров; сам endpoint
  и преобразование в JSON Schema в этом срезе не реализованы.
- `Schema.load()` проверяет структуру, UUID, даты и числа; `Schema.dump()`
  сериализует подготовленные данные. Marshmallow dump не заменяет валидацию.
  Права доступа и соответствие выборки бизнес-правилам проверяет будущий use-case.
- Неизвестные поля при `load()` отклоняются. В пользовательских печатных
  структурах нет паролей, хешей или иных полных ORM-данных пользователя.

## Общие вложенные структуры

| Схема | Поля |
| --- | --- |
| `UserPrintSchema` | `user_id`, `name`, `login` |
| `MeasurementUnitPrintSchema` | `measurement_unit_id`, `name` |
| `WorkCategoryPrintSchema` | `work_category_id`, `name` |
| `WorkPricePrintSchema` | `work_price_id`, `category` (0–4), `price` |
| `WorkPrintSchema` | `work_id`, `name`, nullable `category` и `measurement_unit`, `work_prices[]` |
| `MaterialPrintSchema` | `material_id`, `name`, nullable `measurement_unit` |
| `ObjectPrintSchema` | `object_id`, `name`, nullable `address` |
| `ProjectPrintSchema` | `project_id`, `name` |
| `ProjectWorkPrintSchema` | `project_work_id`, nullable `project_work_name`, nullable `price` |
| `ProjectMaterialPrintSchema` | `project_material_id`, nullable `project_material_name`, `material`, nullable `price` |

`work_prices` относится к расценкам каталога по разрядам. Для `by_estimate`
используется именно `project_work.price`, а не цена из `work_prices`.
Имена позиции спецификации и каталога сохраняются раздельно; подмена одного
другим или скрытый fallback не выполняются в схеме.

## `work_types` — виды работ

Источник — каталог `works`, не спецификация конкретного проекта.
Корень `WorkTypesTemplateDataSchema`:

```text
works[]: WorkPrintSchema
```

Вложены категория, единица измерения и расценки по разрядам. Эта схема не
требует `project_id`. Новые правила фильтрации каталога не вводятся;
применение существующих фильтров будет определено в сборщике.

## `shift_report` — сменный отчёт

Корень `ShiftReportTemplateDataSchema`:

```text
shift_report: ShiftReportFullPrintSchema
  ...поля реестра
  shift_report_details[]: ShiftReportDetailPrintSchema
  shift_report_materials[]: ShiftReportMaterialPrintSchema
```

Деталь: `shift_report_detail_id`, `work`, nullable `project_work`,
`quantity`, сохранённая `summ`, nullable `summ_by_estimate`.
Стоимость по спецификации — `quantity × project_work.price`; если нет
позиции или цены, значение строки остаётся `null`.

Расход: `shift_report_material_id`, `project_material`, nullable UUID
`shift_report_detail`, `quantity`, nullable `summ_by_estimate`.
Стоимость — `quantity × project_material.price`; при отсутствии цены — `null`.
Материал, название позиции, цена и единица измерения доступны через
`project_material.material` и остальные вложенные поля.

## `shift_report_list` — реестр сменных отчётов

Корень `ShiftReportListTemplateDataSchema`:

```text
shift_reports[]: ShiftReportRegistryPrintSchema
```

Содержит данные реестра: ID и номер смены, исполнителя, спецификацию, объект,
даты, координаты и расстояния начала/окончания, UUID браузеров, признаки
`signed`, `deleted`, `night_shift`, `extreme_conditions`, `short_shift`,
`leave_id`, комментарий, аудит создания/согласования/изменения и обе суммы:
`shift_report_details_sum`, `shift_report_details_summ_by_estimate`.

Для печати `user` и `project` раскрыты в объекты; вместо строковых
`project_name`/`object_name` используются `project.name`/`object.name`.
`signed_by` и `updated_by` также раскрываются через `UserPrintSchema`.
Деталей и материалов в элементе реестра нет. Пагинация HTTP-реестра не является
ограничением будущей печатной выборки: отчёт должен охватывать всю выборку.

## Правила отбора смен для отчётов

Согласовано учитывать только подписанные неудалённые смены
(`signed=true`, `deleted=false`). Период относится к `shift_report.date`,
а не к `created_at`, `date_start` или `date_end`.
При переводе календарного периода в timestamp-границы нужно использовать
начало первого дня и исключающую границу начала дня после `date_to`.

Отменённая из-за отсутствия смена определяется через `leave_id`.
Отдельное правило её исключения не было однозначно подтверждено ответом
на сгруппированный вопрос; перед реализацией сборщика необходимо его уточнить.
Схема хранит `leave_id` и сама не исключает записи.

## `payroll` — зарплатная ведомость

`PayrollRequestSchema` требует `date_from`, `date_to`, `user` — один UUID,
не массив. Одинаковые начало и конец разрешены, обратный период отклоняется.
Параметры запроса не обращаются к БД: существование и права на пользователя
проверяет будущий сценарий.

Корень `PayrollTemplateDataSchema`:

```text
parameters:
  date_from: date
  date_to: date
  user: UserPrintSchema
user: UserPrintSchema
data[]:
  date: date
  leave[]: LeavePrintSchema
  shift_report[]: ShiftReportWithDetailsPrintSchema
total_summ: number
```

В `parameters.user` — тот же выбранный исполнитель, что и в корневом `user`.
Схема входного запроса содержит UUID, а печатные параметры — разрешённый
объект исполнителя, чтобы можно было вывести его имя в шаблоне.

На каждый календарный день периода формируется одна строка, включая дни без
смен и отсутствий. Дни идут по возрастанию. Отсутствие, пересекающее период,
попадает в `leave` каждого покрываемого дня внутри периода; исходные границы
отсутствия сохраняются, не обрезаются в печатной структуре.

`LeavePrintSchema`: `leave_id`, `start_date`, `end_date`, `reason`,
`reason_label`, nullable `comment`. Причины: `vacation` — «Отпуск»,
`sick_leave` — «Больничный», `day_off` — «Отгул».
Удалённые отсутствия не должны попадать в рабочую выборку.

В `shift_report` — смены выбранного пользователя за этот день с деталями;
материалы смены для ведомости не требовались и в эту структуру не включены.

`total_summ` соответствует `by_estimate` существующей статистики:

```text
SUM(shift_report_details.quantity × project_works.price)
```

Учитываются только детали выбранных смен. Как в существующем SQL SUM,
строки без позиции/цены не дают слагаемого; пустой итог равен `0`.
Отсутствия отображаются информационно, начислений по ним нет.
Не использовать сохранённую `detail.summ` или добавлять стоимость материалов
к зарплатному итогу.

## `object_report` — отчёт по объектам

`ObjectReportRequestSchema`: обязательные `date_from`, `date_to`,
необязательные массивы UUID `users`, `projects`. Отсутствующий или пустой
массив означает отсутствие соответствующего фильтра; `null` и одиночный UUID
вместо массива отклоняются. Это техническое представление необязательного
фильтра, а не ограничение доступа к данным.

Корень `ObjectReportTemplateDataSchema`:

```text
parameters:
  date_from: date
  date_to: date
  users[]: UserPrintSchema
  projects[]: ProjectPrintSchema
objects[]:
  object_id, name, address
  projects[]:
    project_id, name
    works[]:
      project_work: ProjectWorkPrintSchema
      work: WorkPrintSchema
      quantity: number
      summ: number
    materials[]:
      material: MaterialPrintSchema
      quantity: number
      summ: number
```

Печатные параметры содержат выбранные пользователем фильтры, раскрытые для
вывода имён; пустой массив обозначает, что фильтр не задан, а не список всех
исполнителей/проектов, фактически встретившихся в результате.

Источник — подходящие смены реестра и их детали/расходы, но сами смены не
передаются в результирующей иерархии.

- Работа группируется по `project_work_id` внутри проекта. Количество — сумма
  `quantity` подходящих деталей, стоимость — сумма их `quantity × price`
  по связанной позиции спецификации. Детали без `project_work` исключаются.
- Материал группируется по `project_material.material` (`material_id`) внутри
  проекта. Количество — сумма расхода, стоимость — сумма
  `shift_report_material.quantity × project_material.price` по каждой строке.
  Разные строки спецификации одного материала могут иметь разные цены;
  общая сумма не вычисляется умножением общего количества на первую цену.
- Для отсутствующей цены действует семантика `by_estimate`: NULL-слагаемые
  не входят в SUM, пустой денежный итог равен нулю. Количество не теряется.
- Работы и материалы всегда остаются разными разделами, включая совпадающие
  названия. Ключи группировки — ID, а не названия.
- Проект без работ и материалов не выводится; объект без оставшихся проектов
  также не имеет данных для вывода. Проект только с материалами допустим.
- Нулевое количество само по себе не означает отсутствие строки. Новые
  фильтры по нулевому результату или удалённости справочников не вводятся.

Схемы не реализуют эти группировки и не пересчитывают суммы. Корректность
подготовленного результата, одинакового пользователя ведомости и непрерывного
календаря должен обеспечить будущий сборщик и его бизнес-тесты.

## Проверки

```bash
.venv/bin/pytest --noconftest -q tests/test_template_data_schemas.py
```

Проверяются все пять типов, полнота вложенных полей, русские метаданные,
JSON-сериализация UUID/дат/Decimal, структура реестра, пустые дни и массивы,
разделение агрегатов, обязательность периода и одного пользователя,
некорректные UUID/даты/фильтры/нечисловые значения, запрет неизвестных полей.
Тесты не требуют PostgreSQL, S3 или template-service.
