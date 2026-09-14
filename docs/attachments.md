# Вложения

## Хранение

Вложения хранятся в S3-совместимом хранилище и связаны ровно с одной сущностью:
проектом, сменным отчётом, объектом, местом или приёмкой работ. Повторное связывание уже созданного
`attachment` не поддерживается API.

S3 key формируется по шаблонам:

- `ok-service/projects/{project_id}/{attachment_id}_{filename}`;
- `ok-service/shift_reports/{shift_report_id}/{attachment_id}_{filename}`;
- `ok-service/objects/{object_id}/{attachment_id}_{filename}`.
- `ok-service/places/{place_id}/{attachment_id}_{filename}`.
- `ok-service/acceptances/{acceptance_id}/{attachment_id}_{filename}`.

UUID предотвращает перезапись файлов с одинаковыми именами. Исходные данные файла
хранятся в `attachments`: нормализованное имя, размер, SHA-256 checksum, MIME-тип,
расширение, время и автор создания. Время соответствует общему контракту проекта —
Unix timestamp в миллисекундах.

## API

Для каждого типа сущности доступны одинаковые операции:

```text
POST   /projects/{project_id}/attachments
GET    /projects/{project_id}/attachments
GET    /projects/{project_id}/attachments/{attachment_id}/download
DELETE /projects/{project_id}/attachments/{attachment_id}
```

Префикс `projects` заменяется на `shift_reports`, `objects`, `places` или `acceptances` для
соответствующей сущности.

Загрузка использует `multipart/form-data`. Каждый файл передаётся повторяемым полем
`files`. Batch атомарен на уровне API: если валидация, S3 или запись в БД завершается
ошибкой, уже загруженные в рамках запроса S3-объекты удаляются компенсирующей
операцией.

Detail views `GET /projects/{project_id}/view`,
`GET /shift_reports/{shift_report_id}/view` and
`GET /objects/{object_id}/view`, `GET /places/{place_id}/view` include an
`attachments` array. Each item
contains attachment metadata without a download URL.
The array is empty when the entity has no attachments. `/all` responses are
unchanged. Access follows the original entity view endpoint. To preview or
download bytes, call the attachment `/download` endpoint.

`GET /acceptances/{acceptance_id}/view` также включает массив `attachments`.

## Права

- Вложения проекта: `admin` и `manager` — любой проект; `project-leader` — только
  проект, где он указан в `project_leader`.
- Вложения объекта и места: просматривать и скачивать могут все роли, включая
  `user`; добавлять и удалять — только `admin`.
- Вложения сменного отчёта: `user` видит и скачивает вложения только собственной
  смены, то есть при `shift_reports.user == current_user`; `manager` и любой
  `project-leader` видят и скачивают вложения смены. До согласования
  (`signed=false`) добавлять и удалять вложения могут `admin`, любой `manager`,
  project leader текущего project и владелец смены с ролью `user`. После
  согласования (`signed=true`) добавлять и удалять вложения могут `admin`,
  любой `manager` и project leader текущего project. Отчёт, связанный с
  отсутствием через `leave_id`, не изменяется.
- Вложения приёмки работ: просматривать и скачивать могут все аутентифицированные
  пользователи; добавлять и удалять — только `admin` и `manager`.
- Удалённые сущности не принимают изменения вложений.

Hard delete сущности с вложениями блокируется внешним ключом. Сначала вложения
удаляются через attachment API, чтобы не оставлять orphan-файлы в S3.

## Валидация файлов

PNG и JPEG/JPG перед сохранением автоматически преобразуются в WebP с качеством 80.
Для таких файлов в хранилище и метаданных вложения используются расширение `.webp`,
MIME-тип `image/webp`, размер и checksum уже преобразованного содержимого.

Один файл не превышает 100 MiB. Разрешены документированные форматы документов,
изображений, аудио, видео и ZIP. Проверяются имя, расширение, MIME-тип и сигнатура;
исполняемые файлы и ZIP с исполняемым содержимым отклоняются.
