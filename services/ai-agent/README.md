# AI Agent

## Описание

Stateless микросервис на JavaScript (Node.js 20), симулирующий поведение редактора документов. Агент циклически получает документ из Text Service, генерирует правку через OpenAI API, отправляет её на рассмотрение и публикует информационные сообщения в Chat Service.

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
- `AGENT_ROLE` - роль агента (например, "эксперт по квантовой физике")
- `API_TOKEN` - токен для аутентификации
- `TEXT_SERVICE_URL` - URL Text Service
- `CHAT_SERVICE_URL` - URL Chat Service
- `OPENAI_API_KEY` - ключ ProxyAPI для OpenAI

## Цикл работы

1. Запрос документа: `GET /api/document/current`
2. Просмотр сообщений в чате: `GET /api/chat/messages?since=<timestamp>`
3. Генерация правки через OpenAI API
4. Отправка правки: `POST /api/edits`
5. Публикация сообщения: `POST /api/chat/messages`
6. Ожидание 1 секунду
7. Повторение цикла

При получении `429 Too Many Requests` (превышение бюджета) агент завершает работу.

## Обработка ошибок

- Retry логика с экспоненциальным backoff (до 5 попыток)
- Graceful shutdown при исчерпании бюджета
