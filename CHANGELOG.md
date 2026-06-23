# CHANGELOG

## [Unreleased]

### Добавлено

- Добавлен `README.md` как входная точка в документацию проекта.
- Добавлен `ARCHITECTURE.md` с целевым разрезом `domain / use-case / adapters / web` и правилами зависимостей.
- Добавлен `docs/clean-architecture-transition.md` с поэтапным планом переезда от текущих роутеров и менеджеров к чистой архитектуре.
- В план миграции добавлен первый практический срез на `leaves` как пример разложения по слоям.
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
