# ok-service-backend

Этот репозиторий использует документированную архитектуру и план перехода на чистую архитектуру.

## Документация

- [ARCHITECTURE.md](./ARCHITECTURE.md) - правила слоёв, зависимости и границы ответственности.
- [docs/clean-architecture-transition.md](./docs/clean-architecture-transition.md) - поэтапный план переезда.
- [docs/type-system-guidelines.md](./docs/type-system-guidelines.md) - правила типизации, чтобы не размазывать `cast` и `None`-проверки по коду.
- [docs/model-and-swagger-rules.md](./docs/model-and-swagger-rules.md) - правила построения request/response/filter моделей и swagger-контрактов.
- [docs/access-control-rules.md](./docs/access-control-rules.md) - правила прав доступа, ownership и тестового gate перед следующими срезами миграции.
- [docs/shift-report-details-rules.md](./docs/shift-report-details-rules.md) - правила расчёта статистики и статуса `project_work` в ответах `shift_report_details`.
- [docs/project-work-statistics-cache.md](./docs/project-work-statistics-cache.md) - проектирование Redis-кэша агрегированной статистики по работам проекта.
- [docs/time-contract.md](./docs/time-contract.md) - единый контракт Unix timestamp в миллисекундах.
- [docs/attachments.md](./docs/attachments.md) - хранение, API, права и валидация вложений.
- [docs/acceptances.md](./docs/acceptances.md) - сущности приёмок, связи с работами, CRUD API и права доступа.
- [docs/project-status-rules.md](./docs/project-status-rules.md) - статусы спецификаций, переходы и ограничения смен/объектов.
- [docs/object-status-rules.md](./docs/object-status-rules.md) - значения статусов объектов и правило завершения объекта.
