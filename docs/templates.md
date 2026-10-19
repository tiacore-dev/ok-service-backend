# Шаблоны документов

Шаблоны — общий справочник сервиса. Все операции доступны по JWT только ролям
`admin` и `manager`. API key для новых операций не поддерживается.
Существующий `POST /templates/generate` и интеграция с template-service
не изменены и не используют новый справочник автоматически.

## Модель и правила

`template_type` — PostgreSQL enum `template_types` и Python enum `TemplateTypes`:

| Значение enum | Русский label |
| --- | --- |
| `work_types` | Виды работ |
| `shift_report` | Отчет по смене |
| `shift_report_list` | Отчет по смене - список |
| `payroll` | Зарплатная ведомость |
| `object_report` | Отчет по объектам |

В запросах и БД используются только английские значения; русские labels
формируются методом `TemplateTypes.label()`. Русские строки в create/filter
отклоняются с HTTP 400.

Тип обязателен при создании и запрещён в PATCH, даже с прежним значением.
`name` обязателен, от 1 до 255 символов. `description` и `output_file_name`
необязательны, допускают `null`. `is_horizontal`, `is_pdf`, `is_default` —
не nullable boolean с начальным значением `false`.

Для каждого типа допустимо от нуля до одного шаблона с `is_default=true`.
Назначение второго возвращает HTTP 409, существующий шаблон не изменяется.
Частичный уникальный индекс `uq_templates_default_type` защищает правило
при конкурентных запросах. Отдельный индекс создан по `template_type`.
`output_file_name`, `is_horizontal` и `is_pdf` сохраняются для будущей генерации:
скачивание всегда возвращает исходный загруженный файл, без конвертации.

В ответе возвращаются `id`, `name`, `description`, `template_type`, `template_type_label`, `s3_key`,
`file_name`, `content_type`, `output_file_name`, три boolean-флага.
`file_name` — нормализованное имя исходного файла, `content_type` — проверенный
MIME-тип. Значения этих полей и `s3_key` клиент изменить напрямую не может.

## API

| Метод | Путь | Результат |
| --- | --- | --- |
| POST | `/templates/add` | Загрузка одного шаблона, HTTP 201, объект метаданных |
| GET | `/templates/all` | `{"templates": [...]}` |
| GET | `/templates/types/all` | Справочник типов: `{"template_types": [{"value": "work_types", "label": "Виды работ"}, ...]}` |
| GET | `/templates/{id}/view` | Объект метаданных |
| PATCH | `/templates/{id}/edit` | Обновлённый объект метаданных |
| DELETE | `/templates/{id}/delete/hard` | Физическое удаление, HTTP 200 |
| GET | `/templates/{id}/download` | Файл с `Content-Disposition: attachment` |

Список принимает `template_type` (точное значение enum), `offset >= 0`
(по умолчанию 0) и `limit` от 1 до 1000 (по умолчанию 100).
Сортировка: `name`, затем `id`. Фильтрация выполняется до пагинации.
Справочник типов доступен тем же ролям `admin` и `manager`, содержит все пять
значений в порядке таблицы выше и не требует наличия загруженных шаблонов.
В create/view/edit и элементах списка `template_type` — английский код,
`template_type_label` — соответствующее русское название; label недоступен для записи.

Создание принимает `multipart/form-data` с одним файлом в поле `file`
и JSON-строкой метаданных в поле `data`, например:

```json
{"name":"Сменный отчёт","template_type":"shift_report","is_default":true}
```

Редактирование принимает либо JSON с метаданными, либо `multipart/form-data`
с необязательными `data` (JSON-строка) и `file`. Хотя бы одно изменение
обязательно. Поля, отсутствующие в PATCH, сохраняются; явные `null` для
nullable-полей очищают их, `false` снимает boolean-флаги.

```json
{"description":null,"output_file_name":null,"is_default":false}
```

Неизвестные поля, повторные поля `data`/`file`, неверные enum/UUID/boolean,
пустое имя и пустой PATCH возвращают HTTP 400. Отсутствующая авторизация —
401, запрещённая роль — 403, неизвестный шаблон — 404, конфликт дефолта — 409,
превышение лимита файла — 413, недоступность S3 при upload/download — 503.

## S3 и согласованность

Разрешены только `.docx` и `.xlsx` размером до 100 МиБ включительно.
Используется существующая проверка имени, MIME-типа и структуры Office ZIP;
пустые файлы, несоответствие формата и исполняемое содержимое отклоняются.
Имя нормализуется существующим S3-клиентом, без преобразования содержимого.

Ключ: `ok-service/templates/{id}/{upload_uuid}_{file_name}`.
При замене даже файла с тем же именем создаётся отдельный S3-объект.
После успешного commit БД удаляется предыдущий файл. Если запись в БД
завершается ошибкой, новый файл удаляется компенсирующей операцией,
а старый остаётся доступен. Обновления и удаления блокируют строку шаблона.

Удаление сначала фиксирует удаление записи из БД, затем удаляет S3-объект.
Как в API вложений, сбои компенсирующего удаления и очистки после commit
пишутся в журнал с S3-ключом и не откатывают БД. Возможен оставшийся файл
в S3; автоматической повторной очистки в этом срезе нет.

## Миграция и проверка

Перед запуском новой версии: `alembic upgrade head`.
Миграция `20261019120000` создаёт enum, таблицу `templates` и индексы;
новые настройки окружения не нужны, используются текущие настройки S3.
Downgrade удаляет таблицу и enum; файлы в S3 миграция не удаляет.
Следующая миграция `20261019130000` переименовывает русские значения enum
в английские через `ALTER TYPE ... RENAME VALUE`, сохраняя записи, UUID,
файлы и уникальность дефолтного шаблона. Её downgrade возвращает русские значения.
Она применяется и на новой БД, и поверх уже применённой `20261019120000`.

Проверки без БД:

```bash
.venv/bin/pytest --noconftest -q tests/test_stored_templates.py tests/test_template_use_case.py tests/test_template_adapter.py tests/test_attachments_use_case.py tests/test_attachments_models.py tests/test_s3_manager.py
```

Проверки PostgreSQL (только тестовая БД, право создавать временные схемы):

```bash
TEST_DATABASE_URL=postgresql://... .venv/bin/pytest --noconftest -q tests/test_stored_templates_postgres.py
```

Интеграционные тесты создают и удаляют только собственные уникальные схемы;
проверяют upgrade/downgrade, CRUD, rollback конфликта и конкурентное создание
двух дефолтных шаблонов одного типа, а также конкурентную замену файлов.
Реальные запросы к S3 в тестах заменены тестовым клиентом.

Связанные HTTP-тесты и полный набор (также только на тестовой БД):

```bash
.venv/bin/pytest -q tests/test_template_web.py tests/test_attachments_routes.py tests/test_attachment_view_data.py tests/test_stored_templates.py tests/test_stored_templates_postgres.py
.venv/bin/pytest -q --maxfail=3
```
