# AI Agent

## Описание

Stateless микросервис на JavaScript (Node.js 20), симулирующий поведение редактора документов. Агент циклически получает
документ из Text Service, генерирует правку через OpenAI API, отправляет её на рассмотрение и публикует информационные
сообщения в Chat Service.

## Технологии

- JavaScript (ES2024)
- Node.js 20
- axios
- openai npm package
- Docker

## Основной функционал

1. Получение текущей версии документа из Text Service
2. Генерация правки через ProxyAPI к OpenAI API
3. Отправка правки на рассмотрение в Text Service
4. Публикация информационных сообщений в Chat Service
5. Чтение истории сообщений других агентов

## Конфигурация

Агент получает конфигурацию через переменные окружения:

- `AGENT_ID` - уникальный идентификатор агента (автогенерируется если не указан)
- `AGENT_ROLE` - роль агента (например, "эксперт по квантовой физике")
- `API_TOKEN` - токен для аутентификации
- `TEXT_SERVICE_URL` - URL Text Service
- `CHAT_SERVICE_URL` - URL Chat Service
- `OPENAI_API_KEY` - ключ ProxyAPI для OpenAI (обязательный)
- `PROXY_API_ENDPOINT` - endpoint ProxyAPI (по умолчанию: https://api.proxyapi.ru/openai/v1)
- `CYCLE_DELAY_MS` - задержка между циклами в миллисекундах (по умолчанию: 1000)
- `MAX_RETRIES` - максимальное количество повторов при ошибке (по умолчанию: 5)

## Цикл работы

1. Запрос документа у text-service: `GET /api/document/current`
2. Просмотр сообщений в чате у chat-service: `GET /api/chat/messages?since=<timestamp>`
3. Генерация правки через OpenAI API (через ProxyAPI endpoint)
4. Отправка правки в text-service: `POST /api/edits`
5. Публикация сообщения в chat-service: `POST /api/chat/messages`
6. Ожидание (CYCLE_DELAY_MS)
7. Повторение цикла

При получении `429 Too Many Requests` (превышение бюджета) агент завершает работу.

## Обработка ошибок

- Retry логика с экспоненциальным backoff (до 5 попыток)
- Graceful shutdown при исчерпании бюджета
- Graceful shutdown при получении SIGINT/SIGTERM

## Развёртывание

### Необходимые GitHub Secrets

Добавьте следующие секреты в настройки репозитория:

1. **OPENAI_API_KEY** ✅ — API ключ от ProxyAPI (уже добавлен)
2. **API_TOKEN** — токен для аутентификации агентов
3. **DEPLOY_HOST** — SSH хост для развёртывания
4. **DEPLOY_USER** — SSH имя пользователя
5. **DEPLOY_PASS** — SSH пароль

### Автоматическое развёртывание

Развёртывание происходит автоматически при push в ветку `main`.

Workflow запускает на удалённом сервере:
- Все инфраструктурные сервисы (PostgreSQL, Redis)
- Text Service (3 узла: Moscow, Saint Petersburg, Novosibirsk)
- Chat Service
- Analytics Service
- Load Balancer
- AI Agents (по умолчанию 5, можно настроить)

### Ручное развёртывание

1. Перейдите в Actions → Deploy AI Agents
2. Нажмите "Run workflow"
3. Укажите количество агентов (по умолчанию: 5)
4. Нажмите "Run workflow"

### Роли агентов при развёртывании

При развёртывании агенты получают разные роли в циклическом порядке:
1. general editor
2. expert in quantum physics
3. style corrector
4. fact checker
5. grammar expert
6. technical writer
7. copyeditor
8. content strategist
9. research specialist
10. documentation expert

## Локальная разработка

```bash
# Установка зависимостей
npm install

# Запуск в режиме разработки
npm run dev

# Запуск в Docker
docker-compose up ai-agent
```
