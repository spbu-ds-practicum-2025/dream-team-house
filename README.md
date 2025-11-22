# «Распределённая система коллективного редактирования документов с AI-агентами»

## Описание

Учебный проект, демонстрирующий
построение отказоустойчивой распределённой системы. Множество автономных AI-агентов, симулирующих поведение
людей-редакторов, совместно создают текстовый документ, предлагая и согласуя правки. Система реализует ключевые принципы
распределённых вычислений: репликацию данных между географически распределёнными узлами, обработку конкурентных запросов
и обеспечение отказоустойчивости.

## Структура проекта

```
.
├── services/                    # Все сервисы системы
│   ├── ai-agent/               # AI агенты (JavaScript/Node.js 20)
│   ├── text-service/           # Сервис управления документами (Python/FastAPI)
│   ├── chat-service/           # Сервис координации агентов (Python/FastAPI)
│   ├── analytics-service/      # Сервис сбора телеметрии (Python/FastAPI)
│   ├── frontend/               # Веб-интерфейс (Next.js 15)
│   ├── desktop-app/            # Десктопное приложение (C++/Qt 6)
│   └── load-balancer/          # Балансировщик нагрузки (Nginx)
├── docs/                       # ТР (техническое решение), архитектура, UML
├── .github/                    # Шаблоны задач и PR
├── docker-compose.yml          # Конфигурация для локального запуска
└── .env.example                # Пример переменных окружения
```

Каждый сервис в `services/` содержит:
- `README.md` — описание сервиса, API, технологии
- `Dockerfile` — конфигурация контейнера
- Файлы зависимостей (`package.json`, `requirements.txt`, `CMakeLists.txt`)
- Исходный код в `src/` или `app/`

## Быстрый старт

### Предварительные требования

- Docker 24+
- Docker Compose
- Git

### Локальный запуск

1. Склонируйте репозиторий:
   ```bash
   git clone https://github.com/spbu-ds-practicum-2025/dream-team-house.git
   cd dream-team-house
   ```

2. Создайте файл `.env` на основе `.env.example`:
   ```bash
   cp .env.example .env
   # Отредактируйте .env и добавьте ваш OPENAI_API_KEY
   ```

3. Запустите все сервисы:
   ```bash
   docker-compose up -d
   ```

4. Запустите несколько AI агентов (например, 5):
   ```bash
   docker-compose up -d --scale ai-agent=5
   ```

5. Откройте веб-интерфейс:
   ```
   http://localhost:3000
   ```

6. API доступен через Load Balancer:
   ```
   http://localhost/api/document/current
   http://localhost/api/chat/messages
   http://localhost/api/analytics/metrics
   ```

### Остановка системы

```bash
docker-compose down
```

Для полной очистки (включая данные БД):
```bash
docker-compose down -v
```

## Как работать

1. Создайте ветку от `main`.
2. Пишите код в `services/<service>/`.
3. Если меняете архитектуру — обновляйте `docs/tr.md`.
4. Делайте PR в `main` — используйте шаблон PR.

## Требования к PR (минимум)

- Понятное описание
- Обновлённые docs при архитектурных изменениях
- Запускается локально (опишите в `services/<service>/README.md`)
## Implemented Services Status

### ✅ Completed Services

All core services have been fully implemented with comprehensive test coverage:

#### 1. Text Service (Python/FastAPI)
- ✅ PostgreSQL database models (documents, edits, token_budget)
- ✅ Document versioning and retrieval
- ✅ Anchor-based edit operations (insert, replace, delete)
- ✅ Replication between 3 nodes
- ✅ Token budget tracking with 429 responses
- ✅ Analytics event integration
- ✅ **17 unit tests passing**

#### 2. Chat Service (Python/FastAPI)
- ✅ Redis Streams integration (XADD/XRANGE)
- ✅ Message posting and retrieval
- ✅ 1000 message limit with MAXLEN
- ✅ Structured message types (EditIntent, EditComment, EditOperation)
- ✅ **6 unit tests passing**

#### 3. AI Agent (Node.js/JavaScript)
- ✅ Full agent cycle implementation
- ✅ OpenAI ProxyAPI integration with JSON mode
- ✅ Anchor-based text operations
- ✅ Retry logic with exponential backoff
- ✅ Budget limit handling (429 responses)
- ✅ **8 unit tests passing**

#### 4. Analytics Service (Python/FastAPI)
- ✅ Event storage in PostgreSQL
- ✅ Metrics aggregation (1h, 24h, 7d periods)
- ✅ Time-series data generation
- ✅ **5 unit tests passing**

#### 5. Load Balancer (Nginx)
- ✅ Round-robin distribution across 3 Text Service nodes
- ✅ Health checks with max_fails and fail_timeout
- ✅ Automatic failover with proxy_next_upstream
- ✅ Keepalive connections for performance
- ✅ Status monitoring endpoint

### 🎯 Total Test Coverage
**36 unit tests passing** (17 + 6 + 8 + 5)

## Edit Operations

All edit operations use **anchor-based positioning** from `multi_agent_editor_demo_Version2.py`:

### Insert Before/After
```json
{
  "operation": "insert",
  "anchor": "existing text",
  "position": "before",
  "new_text": "text to insert"
}
```

### Replace
```json
{
  "operation": "replace",
  "anchor": "text to find",
  "new_text": "replacement text"
}
```

### Delete
```json
{
  "operation": "delete",
  "anchor": "text to delete"
}
```

## Running Tests

### Python Services
```bash
# Text Service
cd services/text-service
pip install -r requirements.txt
pytest tests/ -v

# Chat Service  
cd services/chat-service
pip install -r requirements.txt
pytest tests/ -v

# Analytics Service
cd services/analytics-service
pip install -r requirements.txt
pytest tests/ -v
```

### AI Agent
```bash
cd services/ai-agent
npm install
npm test
```

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/ci.yml`) includes:

1. **Unit Tests**: All services tested on every push
2. **Docker Builds**: All service images built and cached
3. **Integration Tests**: Services tested together with PostgreSQL and Redis
4. **E2E Tests**: Full system test with Docker Compose (on main/develop)
5. **Code Linting**: Python (flake8) and JavaScript

## API Endpoints

### Text Service
- `GET /health` - Health check
- `GET /api/document/current` - Get current document version
- `POST /api/document/init` - Initialize new document
- `POST /api/edits` - Submit edit from agent
- `GET /api/edits?limit=N&offset=M` - List edits with pagination
- `POST /api/replication/sync` - Accept replication from peer node
- `GET /api/replication/catch-up?since_version=N` - Get missing versions

### Chat Service
- `GET /health` - Health check
- `POST /api/chat/messages` - Post message to chat
- `GET /api/chat/messages?since=<timestamp>&limit=N` - Get messages

### Analytics Service
- `GET /health` - Health check
- `POST /api/analytics/events` - Record event
- `GET /api/analytics/metrics?period=<1h|24h|7d>` - Get aggregated metrics

## Configuration

### Environment Variables

**AI Agent**:
- `AGENT_ROLE` - Agent role/specialization
- `OPENAI_API_KEY` - OpenAI API key
- `OPENAI_BASE_URL` - API base URL (default: ProxyAPI)
- `TEXT_SERVICE_URL` - Text service URL
- `CHAT_SERVICE_URL` - Chat service URL
- `MAX_EDITS` - Maximum edits per agent (default: 5)
- `CYCLE_DELAY_MS` - Delay between cycles in ms (default: 2000)

**Text Service**:
- `DATABASE_URL` - PostgreSQL connection string
- `NODE_ID` - Node identifier (node-a, node-b, node-c)
- `NODE_NAME` - Human-readable node name
- `PEER_NODES` - Comma-separated peer node URLs
- `ANALYTICS_URL` - Analytics service URL

**Chat Service**:
- `REDIS_URL` - Redis connection string

**Analytics Service**:
- `DATABASE_URL` - PostgreSQL connection string

## Architecture Highlights

### Distributed Features
- **Replication**: 3-node Text Service with eventual consistency
- **Concurrency**: Multiple agents editing simultaneously with PostgreSQL transactions
- **Safety**: Transaction-based edits, replication ensures no data loss
- **Liveness**: Automatic node recovery with catch-up mechanism
- **Fault Tolerance**: Load balancer health checks and failover

### Text Operations
Based on `multi_agent_editor_demo_Version2.py`, all operations use text anchors:
- Find exact text fragments (anchor)
- Insert before/after anchor
- Replace anchor with new text
- Delete anchor
- No index-based operations for better reliability

