# Парсинг спецификации через Kimi

## Назначение

Сценарий разбирает загруженный документ и возвращает структурированный JSON для
будущего создания `project_work` и `project_material`. Текущий этап ничего не
создаёт и не изменяет в базе данных.

## Настройки

Клиент Kimi использует серверные переменные окружения:

- `MOONSHOT_API_KEY` — Bearer token;
- `MOONSHOT_MODEL` — идентификатор модели;
- `MOONSHOT_URL` — базовый URL, по умолчанию `https://api.moonshot.ai`.

Текст системного промпта хранится в системной настройке
`system_settings.system_prompt`. Если настройка отсутствует, равна `null` или
содержит только пробелы, запрос к модели не выполняется и возвращается ошибка
`Отсутствует системный промпт`.

## Текущий API

```text
POST /projects/parse-project-specification
Content-Type: multipart/form-data
file: <document>
```

В запрос не передаётся `project_id`: endpoint только парсит документ и не
связан с конкретной спецификацией.

Доступ разрешён:

- JWT-пользователям с ролью `admin`, `manager` или `project-leader`;
- API key с permission `projects-parse-project-specification`.

Для `project-leader` не выполняется проверка ownership: endpoint не читает и
не записывает данные конкретного проекта.

## Обработка

1. Backend загружает файл в Kimi с `purpose=file-extract`.
2. Получает извлечённое Markdown-содержимое.
3. Удаляет временный файл из Kimi независимо от успешности чтения содержимого.
4. Передаёт модели извлечённый текст и полные актуальные справочники работ и
   материалов. В справочниках используются только неудалённые записи.
5. Валидирует JSON-ответ модели и заменяет временные идентификаторы на UUIDv4,
   сгенерированные backend.
6. Возвращает JSON пользователю без записи в БД.

В модель передаются каталоги следующей формы:

```json
{
  "WORK_CATALOG": [{"id": "UUID", "name": "string"}],
  "MATERIAL_CATALOG": [{"id": "UUID", "name": "string"}],
  "DOCUMENT_CONTENT": "Markdown-содержимое документа"
}
```

## Контракт результата

До замены backend-ом модель обязана использовать placeholders
`new-project-work-N` и `new-project-material-N`. Ссылка материала
`project_work` указывает на placeholder работы.

```json
{
  "project_works": [
    {
      "project_work_id": "new-project-work-1",
      "project_work_name": "Монтаж перегородок",
      "work": "UUID из WORK_CATALOG",
      "quantity": 120,
      "price": 5000
    }
  ],
  "project_materials": [
    {
      "project_material_id": "new-project-material-1",
      "material": "UUID из MATERIAL_CATALOG",
      "quantity": 300,
      "price": 120,
      "project_work": "new-project-work-1"
    }
  ],
  "unresolved_items": []
}
```

Backend заменяет `project_work_id`, `project_material_id` и ссылку
`project_work` на реальные UUID. Поля `project`, `signed`, `summ`,
`created_by` и `created_at` на этом этапе не возвращаются и не принимаются.

## Системный промпт

```text
Ты анализируешь документ со спецификацией строительных работ и материалов.
Твоя задача — извлечь структурированные данные для последующего создания
project_work и project_material.

Используй для полей work и material только UUID из переданных справочников.
Не придумывай UUID. Для каждой работы верни project_work_id строго в формате
new-project-work-N, project_work_name, work, quantity и price. Для каждого
материала верни project_material_id строго в формате new-project-material-N,
material, quantity, price и project_work — placeholder связанной работы либо
null. Не возвращай project, signed, summ, created_by, created_at и другие поля.
Если позицию нельзя однозначно сопоставить со справочником, не добавляй её в
массивы, а укажи в unresolved_items с причиной. quantity и price должны быть
JSON-числами. Верни только валидный JSON без Markdown и пояснений.
```

## Импорт результата

```text
POST /projects/{project_id}/import-works-and-materials
```

Endpoint принимает результат парсинга и является единственной точкой записи в
базу. `project_id` из path-параметра будет источником истины: backend не будет
доверять значению проекта из клиентского JSON. Импорт:

1. проверить доступ к указанной спецификации;
2. создать работы и материалы в одной транзакции;
3. подставить созданные `project_work_id` в связанные материалы;
4. применить существующие правила валидации, расчёта `summ` и прав доступа;
5. откатить всю операцию при ошибке любой позиции.

Endpoint реализован как атомарный импорт: API key требует permission
`projects-import-works-and-materials`; JWT доступен `admin` и `manager`, а `project-leader` —
только для своей спецификации.
