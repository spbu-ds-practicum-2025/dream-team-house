# Analytics Service

## Описание

Stateless сервис на Python (FastAPI) для сбора телеметрии и агрегации метрик. Принимает события от Text Service (применение правок, репликация, ошибки) и предоставляет агрегированную статистику для визуализации.

## Технологии

- Python 3.11
- FastAPI
- SQLAlchemy
- PostgreSQL 15
- Docker

## API Endpoints

- `POST /api/analytics/events` - приём события от Text Service
  - Тело запроса: `{event_type: string, agent_id: string, version: number, tokens: number, timestamp: string, metadata: object}`
  - Ответ: `{status: "ok"}`

- `GET /api/analytics/metrics?period=<1h|24h|7d>` - получение агрегированных метрик
  - Параметры:
    - `period` - период агрегации (1h, 24h, 7d)
  - Ответ: 
    ```json
    {
      "total_edits": number,
      "total_tokens": number,
      "active_agents": number,
      "avg_latency_ms": number,
      "edits_per_minute": number,
      "token_usage_by_time": [
        {"timestamp": string, "tokens": number}
      ]
    }
    ```

## Типы событий

### Основные события
- `edit_applied` - правка применена
  - Поля: `agent_id`, `version`, `tokens`, `timestamp`
  
- `replication_success` - успешная репликация
  - Поля: `source_node`, `target_node`, `version`, `latency_ms`
  
- `replication_failed` - ошибка репликации
  - Поля: `source_node`, `target_node`, `error_message`
  
- `budget_exceeded` - превышение бюджета токенов
  - Поля: `total_tokens`, `limit_tokens`
  
- `node_recovered` - восстановление узла после отказа
  - Поля: `node_id`, `downtime_seconds`

## Схема базы данных

### Таблица `events`
- `id` (BIGSERIAL PRIMARY KEY) - уникальный ID события
- `event_type` (VARCHAR) - тип события
- `agent_id` (VARCHAR) - ID агента (если применимо)
- `version` (INT) - версия документа (если применимо)
- `tokens` (INT) - количество токенов (если применимо)
- `timestamp` (TIMESTAMPTZ) - время события
- `metadata` (JSONB) - дополнительные данные в формате JSON

### Индексы
- `idx_events_timestamp` на `events(timestamp DESC)` - фильтрация по времени
- `idx_events_type` на `events(event_type)` - фильтрация по типу события

## Агрегация метрик

### Примеры запросов
- **Общее количество правок**: `SELECT COUNT(*) FROM events WHERE event_type = 'edit_applied'`
- **Общее количество токенов**: `SELECT SUM(tokens) FROM events WHERE event_type = 'edit_applied'`
- **Активные агенты**: `SELECT COUNT(DISTINCT agent_id) FROM events WHERE event_type = 'edit_applied'`
- **Средняя задержка репликации**: `SELECT AVG((metadata->>'latency_ms')::int) FROM events WHERE event_type = 'replication_success'`

## Визуализация

Метрики используются для отображения в:
- **Frontend** (Next.js + Recharts) - веб-дашборд
- **Desktop Application** (C++ Qt + Qt Charts) - нативное приложение

### Графики
- Количество правок во времени (линейный график)
- Потребление токенов по минутам (bar chart)
- Количество активных агентов (число)
- Средняя задержка обработки правок (число)
