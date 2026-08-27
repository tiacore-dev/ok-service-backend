# CHANGELOG

## [Unreleased]

### Добавлено

- Production-деплой (ветка `master`) теперь подключает `docker-compose.prod.yaml`
  с `AWS_CA_BUNDLE` и сертификатом S3; dev и stage используют базовый Compose
  без обязательной переменной `S3_CA_CERT_HOST_PATH`. Новых миграций и изменений
  API нет.

- Исправлена цепочка Alembic: миграция `20260827120000_add_price_to_project_works`
  теперь продолжает актуальную голову `20260818_place_rel_bulk`, поэтому
  `alembic upgrade head` не сталкивается с несколькими головами.

- В `project_works` добавлено nullable-поле `price`; POST и PATCH принимают цену,
  а `summ` рассчитывается как `price * quantity`. Оба поля возвращаются в GET;
  добавлена миграция `20260827120000_add_price_to_project_works`.

- Реализована матрица доступа для объектов, мест, project-place связей,
  связей смена–место и вложений. Учтены привязка `project-leader` к project,
  владелец смены (`shift_reports.user == current_user`) и состояние `signed`;
  миграции, новые настройки и изменения формата API не добавлялись.
- Закрыт просмотр чужих смен: `user` ограничен не только списком, но и
  endpoint-ом detail `/shift_reports/{id}/view`; обновлён устаревший тест доступа
  пользователя к projects.
- Soft delete места теперь возвращает `409`, если место используется в project-place
  или shift-place связи; миграции и формат API не изменялись.
- Project leader теперь может добавлять материалы в собственную спецификацию
  (`project`) и в смену своего project; добавлены проверки ownership и тесты
  для чужих project/смен. Миграции и формат API не изменялись.
- Project leader также получил возможность редактировать и удалять материалы
  собственной спецификации; для чужих project сохранён ответ `403`.
- Пользователю разрешён просмотр объектов, мест, спецификаций (`project`) и
  project-place/shift-place связей; права на изменение этих сущностей не менялись.

- Пользователь видит и изменяет только собственную неподписанную смену;
  после согласования он сохраняет просмотр и скачивание, но не изменяет смену.
- Вложения объектов и мест доступны для просмотра и скачивания всем ролям, а
  изменять их может только `admin`.

- Исправлено скачивание вложений с Unicode-именами: `Content-Disposition` теперь
  формируется в RFC 5987-совместимом виде без невалидного HTTP-заголовка;
  добавлено прикладное логирование этапов download и traceback неожиданных ошибок.

- Добавлены `add-bulk` и `delete-bulk` для связей `places` с проектами и сменами. Массовое добавление возвращает созданные связи, массовое удаление — количество удалённых; существующие и отсутствующие связи пропускаются. Добавлена миграция API-key permissions `20260818_place_rel_bulk`.

- Для сущности Places добавлены связи с вложениями, загрузка, список,
  скачивание и удаление вложений; метаданные добавлены в `GET /places/{id}/view`.
  Добавлена миграция `20260818_place_attachments`; права соответствуют manager
  связанного объекта или admin.

- Добавлено диагностическое логирование загрузки вложений: параметры multipart-файлов без содержимого, пользователь, этап запроса и полный traceback для необработанных ошибок; API-ответы не изменены.
- Ошибки разбора multipart-запроса при загрузке вложений теперь возвращаются как `400 Bad Request`, а не как `500 Internal Server Error`.
- Ошибки превышения лимита multipart-запроса (`RequestEntityTooLarge`) при загрузке вложений теперь возвращаются как `413`, а не как `500`.
- На уровне Flask установлен максимальный размер входящего HTTP-запроса `105 MiB`, что позволяет загружать вложение до `100 MiB` с учётом multipart-overhead.
- Для upload endpoint-ов вложений Swagger теперь принудительно использует `multipart/form-data`; `application/x-www-form-urlencoded` исключён из контракта загрузки файлов.
- Исправлено описание поля `files` в Swagger: оно больше не генерируется как массив form-параметров, из-за которого Swagger UI выбирал `application/x-www-form-urlencoded`; сервер по-прежнему читает все повторяющиеся поля `files` через `getlist`.
- В detail-view проектов, сменных отчётов и объектов добавлен массив `attachments` с метаданными и presigned `download_url`; в `/all` вложения не добавляются.
- Attachment `/download` теперь возвращает бинарное тело файла с `Content-Type` и `Content-Disposition`; ссылки на скачивание удалены из вложений в detail-view.

- Добавлен `PATCH /shift_reports/{id}/sign` для согласования сменного отчёта: endpoint без тела устанавливает `signed=true`, фиксирует согласовавшего и время согласования; `PATCH /shift_reports/{id}/edit` больше не заполняет эти поля при `signed=true`, но очищает их при `signed=false`. Новых миграций и настроек нет.

- Исправлено чтение проектов: `GET /projects/all` и просмотр проекта теперь возвращают исторические записи с некорректными полями, включая пустое имя, без их автоматического исправления или пропуска. Валидация имени остаётся строгой для создания и редактирования проектов; API создания и миграции БД не изменялись.

- Логирование и Prometheus-метрики защищены от дублирования и неограниченной кардинальности: `PrometheusHandler` больше не печатает отладочные строки, считает сообщения только по стабильному label `level`, а HTTP-метрики группируются по шаблону маршрута и не учитывают обращения к `/metrics`.

- Подготовлена Redis-инфраструктура для кэширования агрегатов `project_works`: добавлены зависимость, `REDIS_URL`, ленивый клиент в `app.extensions` и документация пересчёта без TTL.

- Статистика работ проекта перенесена в Redis: агрегаты по `(project_id, work_id)` обновляются после изменения смен, их деталей и строк спецификации; удалённые смены не учитываются. `with_stat` добавлен в `GET /project_works/all`; тесты используют in-memory mock Redis.

- Уточнён запуск Redis-статистики при CI/CD: Redis не поднимается pipeline, а первоначальный пересчёт запускается отдельной командой внутри уже работающего backend-контейнера. Pylance-совместимость тестовых fake-объектов и загрузки миграции приведена к актуальным Protocol-контрактам.

- Redis-статистика восстанавливается из БД при cache miss и не возвращает `500` при временной недоступности Redis; пересчёт добавлен для смен, отменённых leave, а ключ удаляется при жёстком удалении проекта.

- Для конфликтов листов отсутствия с открытыми сменами добавлены структурированный warning-лог и `detail` в ответе `409` с данными блокирующей смены; пересечение смены с листом определяется только по полю `shift_reports.date`.

- Для `GET /roles/all` добавлен permission `roles-list`: endpoint доступен по JWT и API-Key, а миграция добавляет это право ко всем существующим API-ключам.

- В `shift_reports` добавлено nullable-поле `leave_id` и миграция связи со `leaves`: при создании или редактировании листа отсутствия открытые смены (`date_start != null`, `date_end == null`) блокируют операцию с ответом `409`, а неоткрытые смены (`date_start == null`) автоматически помечаются удалёнными и связываются с листом. Создание и редактирование смен проверяют пересечение с активными листами отсутствия.

- Все сохраняемые Unix timestamp-поля унифицированы в миллисекунды: обновлены генераторы времени, ORM и PostgreSQL defaults, проверка срока действия API-ключей, Swagger-описания и добавлена миграция существующих секундных значений.

- Уточнены права роли `user` для `shift_reports`: пользователи не могут создавать, мягко удалять или жестко удалять сменные отчеты, включая обход через `PATCH .../edit` с `deleted=true`.

- Для `positions` добавлены permission types для JWT/API-key доступа ко всему базовому CRUD (`add`, `all`, `view`, `edit`, `delete/hard`) и тест на работу `positions` через `API-Key`.
- В `users` добавлены необязательный FK на `positions` и поле `is_active`: обновлены доменная модель, use-case DTO, web-схемы, swagger-модели, репозиторий, фикстуры тестов и добавлена миграция `positions` + `users.position_id`/`users.is_active`.
- Добавлен базовый CRUD для `positions`: выделены `domain/use-case/adapters/web`-слои, подключен namespace `/positions/*`, добавлены тесты на доменную логику и HTTP-контракт, а ORM-модель `Poitions` приведена к корректному имени `Positions`.
- Ослаблена типизация `app/web/subscriptions`: убраны Pylance-ошибки вокруг `pywebpush` и ключа VAPID, при этом контракт `/subscriptions/*` сохранён.
- Перенесены `roles` и `subscriptions` в `app/web`: web namespace'ы и модели для `/roles/all`, `/subscriptions/*` теперь живут в новом слое, старые файлы из `app/routes` удалены, добавлены тесты для subscriptions.
- Перенесён `auth` в `app/web`: добавлены web-модели и namespace для `/auth/health`, `/auth/login` и `/auth/refresh`, старые файлы из `app/routes` удалены, добавлены тесты на login и refresh.
- Перенесён `api-key` в `app/web`: добавлены web-модели и namespace для `/api-key/*`, старые файлы из `app/routes` удалены, добавлены тесты на создание ключа, основные ручки модуля и негативные сценарии.
- Перенесён `project_schedules` в `app/web`: выделены domain/use-case/adapters/web-слои, сохранён контракт `/project_schedules/*`, а legacy namespace и модели удалены из `app/routes`.
- Перенесены `objects` и `object_statuses` в `app/web`: выделены domain/use-case/adapters/web-слои, сохранены ручки `/objects/*` и `/object_statuses/all`, а legacy namespace и модели удалены из `app/routes`.
- Перенесён `projects` в `app/web`: выделены domain/use-case/adapters/web-слои, сохранён контракт `/projects/*`, а legacy namespace и модели удалены из `app/routes`.
- Перенесён `cities` в `app/web`: добавлены domain/use-case/adapters/web-слои для CRUD и `/cities/all`, а legacy namespace и модели удалены из `app/routes`.
- Убран прямой импорт `app.database.time_utils` из `use_cases`: общий UTC-helper перенесён в `app/use_cases/time_utils.py`, чтобы слой сценариев больше не зависел от `app.database`.
- Перенесён `template` в `app/web`: добавлены domain/use-case/adapters/web-слои для `/templates/generate`, а legacy namespace и модель удалены из `app/routes`.
- Уточнён контракт users-маппера: `UserRecordDict` теперь типизирует форму `UserManager.to_dict()`, чтобы убрать Pylance warnings на UUID/числовых полях.
- Исправлен `POST /users/add`: adapter больше не опирается на неинициализированный `user_id` из `UserManager.add_user()` и читает созданного пользователя по логину после коммита.
- Перенесён `users` в `app/web`: добавлены domain/use-case/adapters/web-слои, а legacy namespace `app/routes/namespaces/user_ns.py` удалён из маршрутизаторов.
- Уточнены типы в use-case для `materials` и `shift_report_materials`, а в unit-тестах убраны обращения к optional-полю репозитория, чтобы не было Pylance warnings по `object | None`.
- Перенесены `materials` и `shift_report_materials` в `app/web`: добавлены domain/use-case/adapters/web-слои, а legacy namespace-файлы удалены из `app/routes/namespaces`.
- Удалён legacy namespace `app/routes/namespaces/work_material_relation_ns.py`; активный транспорт для `work_material_relations` остаётся только в `app/web/work_material_relations/routes.py`.
- Укреплен парсинг JWT identity в `app/decorators/role_decorators.py`, чтобы `admin_required` и `user_forbidden` принимали как JSON-строку, так и уже распарсенный dict.
- Приведены пакетные re-export'ы в `app/database/__init__.py`, `app/database/models/__init__.py` и `app/decorators/__init__.py` к явному alias-формату, чтобы убрать `F401` на публичных импортах.
- Добавлен `README.md` как входная точка в документацию проекта.
- Добавлен `ARCHITECTURE.md` с целевым разрезом `domain / use-case / adapters / web` и правилами зависимостей.
- Добавлен `docs/clean-architecture-transition.md` с поэтапным планом переезда от текущих роутеров и менеджеров к чистой архитектуре.
- В план миграции добавлен первый практический срез на `leaves` как пример разложения по слоям.
- Исправлен контракт `POST /leaves/add`: RESTX-валидация отключена точечно на `expect(...)`, чтобы запросы доходили до use-case и конфликт со сменой возвращался как `409`, а не `422`.
- Приведён `DELETE /users/<user_id>/delete/hard` к общему шаблону hard-delete маршрутов: добавлен `admin_required` и нормализован `user_id` в ответе как строка.
- В `work_prices` выровнен контракт `POST /work_prices/add`: RESTX-валидация отключена точечно на `expect(...)`, чтобы новый web-слой не отрезал запросы до marshmallow/use-case.
- Начат вертикальный срез для `work_categories`: выделены `domain`, `use-case`, `adapters` и `web`, а legacy `work_category_ns` и `work_ns` удалены из `app/routes/namespaces`.
- Начат вертикальный срез для `work_material_relations`: выделены `domain`, `use-case`, `adapters` и `web`, а legacy `work_material_relation_ns` удалён из `app/routes/namespaces`.
- Добавлен начальный `domain`-слой для `leaves`: сущность `Leave`, enum `AbsenceReason`, доменные ошибки и правила периода.
- Добавлен начальный `use-case`-слой для `leaves`: порты, DTO и сценарии create/get/update/delete/list.
- Добавлены `adapters` и `web`-слои для `leaves`, а регистрация namespace перенесена через `app/web`.
- Удалена старая реализация `leave_ns`; теперь `leaves` обслуживается только через `app/web/leaves/routes.py`.
- Уточнены типы в `leaves`-мэпперах и web-слое, чтобы убрать предупреждения Pylance по `UUID | None` и `request` payload-ам.
- Добавлен отдельный документ с правилами типизации `web`-слоя и DTO/mapper-гигиены.
- В `ARCHITECTURE.md` добавлен контракт по типизации `web`, а в `README.md` - ссылка на отдельные правила типов.
- В `ARCHITECTURE.md` добавлен отдельный контракт по общим helper-ам `adapters`-слоя для mapper/repository преобразований.
- Добавлен общий модуль helper-ов `app/web/_typing.py` для нормализации payload, UUID-конверсий и безопасного доступа к optional полям.
- Добавлен общий модуль `app/adapters/_typing.py` для UUID-конверсий и нормализации результатов в adapters-слое.
- В `ARCHITECTURE.md` описано, что общие преобразования типов для adapters должны жить в `app/adapters/_typing.py`, а не дублироваться в mapper/repository.
- Исправлена ранняя инициализация `Session` в менеджерах: `BaseDBManager` и `LogManager` теперь берут `db_globals.Session` лениво, чтобы `set_db_globals(...)` не оставался незамеченным.
- Добавлен общий helper `app/database/time_utils.py` для timezone-aware UTC-времени и переведены модели на него вместо `datetime.utcnow()`.
- Поля `created_at` и `timestamp` в моделях БД переведены на единый UTC-helper, чтобы убрать предупреждения `datetime.utcnow()` и не дублировать локальные `lambda`.
- Обновлены модели `app/database/db_setup.py` и marshmallow-схемы: `declarative_base()` переведён на актуальный импорт, `missing` заменён на `load_default`, а описания полей перенесены в `metadata`.
- Добавлен `pytest.ini` с точечным фильтром на внешний warning `flask_restx` про deprecated `jsonschema.RefResolver`, чтобы не засорять вывод тестов предупреждениями из `site-packages`.
- Начат полный вертикальный срез для `work_prices`: выделены `domain`, `use-case`, `adapters` и `web`, а старый `work_price_ns` удалён.
- Исправлен `GET /shift_reports/all`: отсутствие query-параметров `user` и `project` больше не превращается в пустой список фильтров, поэтому пользователь снова видит свои отчёты, а админ - все доступные записи.
- Для `work_prices` добавлены unit-тесты на доменную валидацию и сценарии create/update без БД.
- В `app/web/work_prices/routes.py` добавлены явные `TypedDict`/`cast` на границах `marshmallow.load()`, чтобы убрать предупреждения Pylance по `Unknown`/`None`.
- Начат вертикальный срез для `project_materials`: выделены `domain`, `use-case`, `adapters` и `web`, а старый `project_material_ns` удалён.
- Для `project_materials` добавлены unit-тесты на доменную валидацию и сценарии create/update без БД.
- Расширен общий helper-слой типизации в `app/web/_typing.py`: добавлены helper-ы для required/optional UUID, `Decimal`, scalar-полей и проверки присутствия ключа в `TypedDict`.
- Обновлены правила типизации в `docs/type-system-guidelines.md`, чтобы новые web-слои опирались на общий helper-контур и не дублировали локальные проверки optional-полей.
- Добавлен отдельный документ с правилами построения моделей и swagger-контрактов: create/edit/response/filter модели теперь описаны отдельно.
- Добавлен отдельный документ по правам доступа, ownership и тестовому gate перед следующими срезами миграции.
- В `docs/clean-architecture-transition.md` зафиксирован тестовый gate: новый срез нельзя продолжать без проверок domain/use-case, route contract и прав доступа.
- Начат вертикальный срез для `project_works`: выделены `domain`, `use-case`, `adapters` и `web`, а старый `project_work_ns` удалён.
- Для `project_works` добавлены unit-тесты на доменную валидацию и сценарии create/update/delete без БД.
- В `project_works` вынесены правила ownership и signed-state в use-case, а bulk/create/list/edit/delete переведены на новый web-слой.
- Расширен общий web-helper-контур: добавлен `get_optional_float(...)` и `get_required_float(...)` для числовых query/body полей.
- Для legacy `PATCH`-эндпоинтов в namespaces `users`, `cities`, `works`, `projects`, `objects`, `materials`, `work_categories`, `work_material_relations`, `shift_reports` и `shift_report_materials` добавлены отдельные `edit`-модели и переведён swagger-контракт с `create_model` на `edit_model`.
- Ослаблена доменная валидация `project_works`: количество теперь допускает ноль, чтобы исторические записи из БД не падали при просмотре и удалении.
- Исправлен `ProjectWorksManager`: `update` и `delete` теперь возвращают `to_dict()` внутри активной сессии, чтобы `project_works` не отдавали detached ORM-объекты и не ломали `edit`/`soft delete` 500-ми.
- Начат общий bounded context `shift_reports`: добавлены доменные сущности `ShiftReport` и `ShiftReportDetail`, use-case контракты и SQLAlchemy-адаптер поверх текущих менеджеров.
- Дочищен `shift_reports`: ролевые правила для create/update/list перенесены в `use-case`, а `web`-слой оставлен только для транспорта и helper-ов типизации.
- Начат вертикальный срез для `works`: выделены `domain`, `use-case`, `adapters` и `web`, а legacy `work_ns` переведён в shim.
- В `ShiftReportsDetailsManager` исправлены `update_shift_report_details` и `delete`, чтобы они возвращали `to_dict()` внутри сессии и не отдавали detached ORM-объекты.
- Для `shift_reports` и `shift_report_details` разнесены DTO для вложенного создания и standalone создания деталей, чтобы репозиторий сам проставлял `shift_report`, а роутер не тащил лишний контракт.
- Расширен общий helper-слой типизации `app/web/_typing.py`: добавлены helper-ы для list-like query params (`get_optional_str_list`, `get_optional_uuid_list`) и обновлены правила их использования.
- Для вложенной `ShiftReportDetailSchema` поле `summ` сделано вычисляемым на сервере, чтобы create-пayload не требовал значение, которое клиент не должен передавать.
- RESTX-валидация на edit-роутах отключена в пользу marshmallow-валидации, чтобы убрать pre-handler `422` и держать контракт в одном месте.
- Удалены старые legacy namespace-файлы `shift_report_ns.py` и `shift_report_detail_ns.py`, чтобы `shift_reports` обслуживался только через новый `web`-слой.
- В `ShiftReportsManager` добавлена нормализация UUID на границе и защита `count_summ` от отсутствующей `shift_report`/`user`, чтобы create-flow не падал `500`.
- Глобальный `RESTX_VALIDATE` убран, а `validate=False` оставлен точечно на проблемных `expect`, чтобы не отключать RESTX-проверки шире необходимого.
- В `shift_reports` добавлен доменный `409 Conflict` для пересечения со `leave`, а update-сценарий теперь проверяет этот конфликт так же, как create.
- Исправлен маппер `shift_report_detail_dict_to_entity`, который должен читать вложенную форму `to_dict()` и не падать на `project_work`/`shift_report`.
- В `docs/type-system-guidelines.md` и `docs/access-control-rules.md` зафиксированы правила для helper-слоя типизации, `TypedDict`-границ и переноса ownership-проверок из роутера в use-case/domain policy.
- В `ShiftReportsManager` отделена проверка leave-конфликта от soft delete: update теперь проверяет пересечение только для изменений временного окна, а soft delete больше не падает на `None` в датах.
- Для `shift_reports` разнесены сообщения доменного конфликта: create сохраняет прежний текст, а edit возвращает `Shift date intersects with existing leave`, как ожидают тесты.
- Для `shift_report_details` update теперь не затирает обязательные FK значениями `None`, а response-mapper снова отдаёт вложенную форму `shift_report`/`project_work`, которую ждут тесты.
- Доменная модель `ShiftReportDetail` расширена дополнительными metadata-полями для web-response, чтобы не терять `shift_report.user_id` и `shift_report.date` при проходе через use-case слой.
- В `shift_reports` добавлены явные типы для query-string нормализации и `get_project_ids_by_leader` в `ShiftReportsManager`, чтобы убрать новые Pylance-ошибки на `list[str]` и отсутствующий метод.
- В `shift_report_details` роутере убраны прямые индексирования `request.json` и `dict[...]`-доступы к optional payload; вход теперь нормализуется через локальные typed-variables.
- В `shift_report_details` роутере `schema.load(...)` теперь явно приводится к `dict[str, Any]`, чтобы Pylance не размечал `get(...)` и индексирование как работу с `Unknown`.
- В тестовом `FakeRepository` для `shift_reports` use-case добавлены недостающие методы `ShiftReportRepository`, чтобы мок соответствовал протоколу без `type: ignore`.
- В тестовом `FakeRepository` уточнены типы `create_shift_report_detail` и `detail_result`, чтобы мок возвращал `ShiftReportDetail`, а не `object | None`.
- В `ARCHITECTURE.md` добавлен сквозной контракт типизации: нормализация на границах слоёв, запрет на протаскивание `Any/Unknown`, правила для `cast`, `None` и тестовых `Protocol`-моков.
- Исправлен `GET /projects/all`: список больше не падает с `400 Project name is required` из-за отдельных legacy-записей с некорректным именем; такие записи пропускаются, при этом create/update/get-by-id сохраняют строгую доменную валидацию.
- В `shift_reports` добавлены nullable-поля аудита согласования и изменений (`signed_by`, `signed_at`, `updated_by`, `updated_at`) с автоматическим заполнением из JWT при PATCH и отображением `id`, `login`, `name` пользователя в GET.
- В ответы `shift_report_details/all` и `all-by-reports` добавлена статистика `project_work` по существующему механизму `get_project_stats`: план, факт и статус `not_checked`/`partial`/`accepted`.
- Добавлена документация правил расчёта статистики и `acceptance_status` для `shift_report_details`.
- В документации уточнено, что расчёт `shift_report_details` основан на `GET /projects/{project_id}/get-stat`.
- Исправлена генерация Swagger-схемы: вложенные модели пользователей `ShiftReportUser` и `ShiftReportUpdater` теперь зарегистрированы в namespace `shift_reports`.
- В `GET /project_works/{project_work_id}/view` добавлены `project_work_quantity` и `shift_report_details_quantity` по правилам `get_project_stats`.
- Для `shift_reports` добавлены `PATCH /{id}/start` и `PATCH /{id}/finish`; время и координаты теперь фиксируются отдельными операциями, а поля старта/завершения убраны из основного PATCH.
- Обновлён устаревший тест редактирования `shift_report`: координаты больше не изменяются через основной PATCH и проверяются как неизменённые.
- Восстановлено старое поведение создания `shift_reports`: `created_by` всегда заполняется из JWT/API key, а роль `user` по-прежнему не может подменить поле `user`.
- Для `shift_reports` добавлено правило доступа: роль `user` не может создавать сменные отчёты; `created_by` при создании остаётся пользователем из JWT/API key.
- Актуализирован тест создания `shift_report`: запрос выполняется от администратора, а поле `user` проверяется отдельно от `created_by`.
* Исправлено чтение сменных отчётов: `GET /shift_reports/all` и просмотр теперь возвращают исторические записи с некорректным порядком `date_start/date_end`, не изменяя их значения. Для `start/finish` сохранены ограничения порядка операций и запись времени через текущий Unix timestamp; добавлена защита от старта отчёта, у которого уже есть финиш.
* Для `shift_reports` ручное редактирование снова принимает даты и координаты начала/окончания смены. Автоматические `start/finish` теперь записывают `date_start/date_end` в миллисекундах; старые значения не изменяются автоматически.
- Добавлен параметр `with_stat` в `GET /shift_report_details/all` и `POST /shift_report_details/all-by-reports`: статистика деталей вычисляется и возвращается только при значении `true`; API и миграции базы данных не изменялись.
## 2026-08-04

- Исправлена миграция `measurement_units`: историческое значение `шт` без точки теперь также преобразуется в справочную единицу `шт.`; новая единица и новая миграция не добавляются.
- В миграцию `measurement_units` добавлена справочная единица `м2`; исторические значения `м2` в `works` и `materials` будут перенесены в неё.

- Исправлено чтение `work_prices`: исторические записи с `null` в `category` или `price` больше не роняют GET `/work_prices/all` и просмотр; входные POST/PATCH по-прежнему требуют заполненные обязательные поля. Исправление существующих данных выполняется вручную при необходимости.

- Добавлен справочник `measurement_units` с единицами `м`, `шт.` и `0.1 м (10 см)` и административным CRUD без soft delete.
- `works.measurement_unit` и `materials.measurement_unit` переведены со строк на nullable FK; API принимает UUID, а возвращает вложенный объект единицы измерения. Миграция нормализует историческое значение `м.` в `м` и отклоняет неизвестные значения.
- Исправлено обновление `works` и `materials`: вложенный объект единицы измерения корректно преобразуется обратно в UUID при редактировании и soft delete.
- Для смен, отменённых из-за отсутствия и связанных через `leave_id`, полностью заблокированы PATCH и операции `start`/`finish` с ответом `409`; при hard delete отсутствия связанные смены сначала отвязываются без восстановления, затем удаляется запись отсутствия.
## 2026-08-11

- Добавлены сущность `attachments` и связи с проектами, сменными отчётами и объектами; идентификаторы и время приведены к контракту проекта, `company_id` не используется.
- Типизация маппера вложений и связанных тестов уточнена для строгой проверки Pylance без изменения API-контракта.
- Добавлены multipart endpoint-ы загрузки нескольких файлов, списка, download URL и удаления для `/projects`, `/shift_reports` и `/objects`; права повторяют ownership соответствующих сущностей.
- Добавлена миграция `20260811_attachments` с API-key permissions; hard delete сущности с вложениями блокируется до их удаления. API использует единый S3 endpoint, миграции настроек API не добавлялись.
- Добавлен публичный `GET /auth/health/s3`: endpoint проверяет доступность S3 bucket без изменения данных и возвращает `200` либо `503`.
- Исправлен S3-менеджер: параметры подключения читаются из переменных окружения, операции используют единый endpoint, а сообщения пишутся через общий логгер `ok_service`.
- Для вложений в S3 добавлена проверка размера до 100 MiB, allowlist документов, медиафайлов и ZIP-архивов, MIME-типа и сигнатуры содержимого; исполняемые файлы отклоняются.

- Добавлена сущность Places: CRUD-эндпоинты, связь с Objects через `object_id`, soft и hard delete.
- GET Places возвращает все поля и устойчив к невалидным историческим значениям; POST/PATCH используют валидацию входных данных.
- В ответ `GET /objects/<object_id>/view` добавлен список привязанных мест `places`; список объектов не изменён.
- Добавлена Alembic-миграция `20260811_places`.

## 2026-08-11

- Добавлены связи мест со спецификациями и сменами, с проверкой соответствия объекта и состава спецификации.
- Добавлен фильтр `place_id` для списка смен и API-key permissions для CRUD связей мест.
