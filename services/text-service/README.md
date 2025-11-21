# Text Service

## Описание

Stateful распределённый сервис на Python (FastAPI), управляющий документом. Обрабатывает запросы на получение текущей
версии документа, принимает и автоматически применяет правки, реплицирует изменения между тремя географически
распределёнными узлами, контролирует бюджет потраченных токенов.

## Технологии

- Python 3.11
- FastAPI
- SQLAlchemy
- asyncio
- aiohttp
- PostgreSQL 15
- Docker

## Архитектура

Три независимых узла с собственными базами данных PostgreSQL:

- Text Service A (Москва)
- Text Service B (Санкт-Петербург)
- Text Service C (Новосибирск)

## API Endpoints

### Документы

- `GET /api/document/current` - получение последней версии документа
- `POST /api/document/init` - создание нового документа с начальным текстом

### Правки

- `POST /api/edits` - приём правки от агента
- `GET /api/edits?limit=N&offset=M` - получение списка правок с пагинацией

### Репликация

- `POST /api/replication/sync` - приём репликационного сообщения от другого узла
- `GET /api/replication/catch-up?since_version=N` - получение версий для восстановления

### Здоровье

- `GET /health` - health check для Load Balancer

## Схема базы данных

### Таблица `documents`

- `version` (INT PRIMARY KEY) - номер версии документа
- `text` (TEXT) - текст документа
- `timestamp` (TIMESTAMPTZ) - время создания версии
- `edit_id` (UUID) - ID правки, создавшей эту версию

### Таблица `edits`

- `edit_id` (UUID PRIMARY KEY) - уникальный ID правки
- `agent_id` (VARCHAR) - ID агента-автора
- `proposed_text` (TEXT) - предложенный текст
- `position` (VARCHAR) - позиция в документе
- `tokens_used` (INT) - количество использованных токенов
- `status` (VARCHAR) - статус правки (pending/accepted/rejected)
- `created_at` (TIMESTAMPTZ) - время создания

### Таблица `token_budget`

- `id` (INT PRIMARY KEY DEFAULT 1) - ID записи
- `total_tokens` (BIGINT) - общее количество использованных токенов
- `limit_tokens` (BIGINT DEFAULT 15000000) - лимит токенов

## Репликация

- **Модель**: Eventual consistency
- **Алгоритм разрешения конфликтов**: Last-write-wins по timestamp
- **Максимальное время достижения консистентности**: 3 секунды
- **Восстановление**: Механизм catch-up для отстающих узлов

## Контроль бюджета

- Жёсткий лимит: ~15,000,000 токенов (≈15,000 рублей)
- При превышении: возврат `429 Too Many Requests`
- Блокировка новых правок до ручного изменения лимита в БД

## Интеграция

- Отправка событий в Analytics Service после каждой операции
- Маршрутизация через Load Balancer (Nginx)
