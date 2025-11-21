# Chat Service

## Описание

Stateless сервис на Python (FastAPI) для координации агентов через обмен информационными сообщениями. Использует Redis
Streams для хранения последних 1000 сообщений.

## Технологии

- Python 3.11
- FastAPI
- redis-py
- Redis 7 (Streams)
- Docker

## API Endpoints

- `POST /api/chat/messages` - приём сообщения от агента
    - Тело запроса: `{agent_id: string, message: string}`
    - Ответ: `{message_id: string, timestamp: string}`

- `GET /api/chat/messages?since=<timestamp>&limit=<number>` - получение истории сообщений
    - Параметры:
        - `since` - timestamp для фильтрации новых сообщений
        - `limit` - максимальное количество сообщений
    - Ответ: `[{agent_id: string, message: string, timestamp: string}, ...]`

## Хранилище данных

### Redis Streams

- **Stream**: `chat:messages`
- **Команды**:
    - `XADD chat:messages MAXLEN ~ 1000 * agent_id <id> message <text> timestamp <ts>`
    - `XRANGE chat:messages <start_id> + COUNT <limit>`

### Персистентность

- AOF (Append-Only File)
- `fsync` каждую секунду
- Хранятся только последние 1000 сообщений (автоудаление старых)

## Сценарии использования

### Координация агентов

1. Агент 1 публикует сообщение о работе над секцией X
2. Chat Service сохраняет в Redis Stream
3. Агент 2 периодически запрашивает новые сообщения
4. Агент 2 узнаёт о работе Агента 1 и выбирает другую секцию

### Типичные сообщения агентов

- "Working on section X"
- "Proposing grammar correction in paragraph Y"
- "Reviewing factual accuracy of introduction"
- "Adding references to quantum mechanics section"

## Ограничения

- Хранятся только последние 1000 сообщений
- Более старые сообщения автоматически удаляются (Redis MAXLEN)
- Отсутствует поиск или фильтрация по содержимому сообщений
- Простая хронологическая сортировка по timestamp
