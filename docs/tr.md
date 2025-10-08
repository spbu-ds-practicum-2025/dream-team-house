# Техническое решение проекта «Распределённая система коллективного редактирования документов с AI-агентами»

## Введение

«Распределённая система коллективного редактирования документов с AI-агентами» — это учебный проект, демонстрирующий
построение отказоустойчивой распределённой системы. Множество автономных AI-агентов, симулирующих поведение
людей-редакторов, совместно создают текстовый документ, предлагая и согласуя правки. Система реализует ключевые принципы
распределённых вычислений: репликацию данных между географически распределёнными узлами, обработку конкурентных запросов
и обеспечение отказоустойчивости.

- **Цель проекта:**  
  Реализовать прототип распределённой системы коллективного редактирования документов, демонстрирующий механизмы
  репликации, обработки конкурентных изменений и отказоустойчивости при участии множества автономных AI-агентов.

- **Задачи:**
    - Закрепить теоретические основы распределённых систем (concurrency, safety, liveness, репликация,
      партиционирование).
    - Реализовать систему с использованием современных технологий (JavaScript для агентов, Python для сервисов, Next.js
      15 для фронтенда, C++ Qt для десктопного приложения).
    - Обеспечить автоматизированное тестирование системы в CI/CD.

- **Основания для разработки:**  
  Учебный проект в рамках курса «Основы распределённых вычислений».

- **Команда:**

| Роль                           | ФИО                          |
|--------------------------------|------------------------------|
| Team Lead, Fullstack Developer | Сухоплечев Виталий Павлович  |
| Fullstack Junior Developer     | Митусов Иван Алексеевич      |
| Fullstack Junior Developer     | Столярова Полина Николаевна  |
| Fullstack Junior Developer     | Егорова Виктория Геннадьевна |

---

## Глоссарий

| Термин                             | Определение                                                                                                                                                                                                                                                                                              |
|------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **AI-агент (Agent)**               | Stateless микросервис на JavaScript, симулирующий редактора. Циклически получает документ из Text Service, генерирует правку через OpenAI API, отправляет её на рассмотрение. Публикует и просматривает информационные сообщения в Chat Service.                                                         |
| **Правка (Edit)**                  | Предложенное изменение фрагмента документа. Содержит идентификатор автора-агента, текст изменения, позицию в документе, количество использованных токенов и timestamp. Автоматически одобряется при отсутствии конфликтов.                                                                               |
| **Документ (Document)**            | Текстовый артефакт с версионностью, хранящийся в распределённой системе. Каждая версия имеет уникальный номер, timestamp и связана с конкретной правкой.                                                                                                                                                 |
| **Text Service**                   | Распределённый stateful сервис на Python, управляющий документом. Обрабатывает запросы на получение текущей версии документа, принимает и автоматически применяет правки, реплицирует изменения между несколькими географически распределёнными узлами (min 3), контролирует бюджет потраченных токенов. |
| **Узел Text Service (Node)**       | Независимый экземпляр Text Service с собственной базой данных PostgreSQL. Узлы синхронизируются через HTTP REST API для обеспечения eventual consistency.                                                                                                                                                |
| **Репликация (Replication)**       | Процесс синхронизации изменений документа между тремя узлами Text Service. При применении правки узел-источник отправляет репликационное сообщение двум другим узлам через `POST /api/replication/sync`. Конфликты разрешаются по timestamp.                                                             |
| **Chat Service**                   | Сервис на Python для координации агентов. Принимает сообщения от агентов через `POST /api/chat/messages` и предоставляет историю через `GET /api/chat/messages`. Использует Redis Streams для хранения последних 1000 сообщений.                                                                         |
| **Analytics Service**              | Сервис на Python для сбора телеметрии. Принимает события от Text Service (применение правок, репликация, ошибки) через `POST /api/analytics/events` и агрегирует метрики в PostgreSQL. Предоставляет статистику через `GET /api/analytics/metrics`.                                                      |
| **Токен (Token)**                  | Единица измерения использования OpenAI API. Каждая правка содержит информацию о количестве использованных токенов. Text Service суммирует общий расход и блокирует новые правки при превышении бюджета.                                                                                                  |
| **Инструкция агента (Agent Role)** | Параметр конфигурации агента, определяющий его специализацию (например, "эксперт по квантовой физике", "корректор стиля", "проверяющий факты"). Передаётся агенту при запуске через переменную окружения.                                                                                                |
| **Safety**                         | Свойство системы: принятые правки не теряются при отказах узлов благодаря репликации; документ не переходит в некорректное состояние благодаря транзакционности.                                                                                                                                         |
| **Liveness**                       | Свойство системы: правки обрабатываются в конечном счёте; система не зависает при отказе одного узла благодаря retry логике и перенаправлению запросов.                                                                                                                                                  |
| **Concurrency**                    | Одновременная работа множества агентов и узлов. Text Service обрабатывает конкурентные правки с использованием транзакций PostgreSQL и блокировок на уровне строк документа.                                                                                                                             |
| **Eventual Consistency**           | Модель консистентности, при которой все узлы Text Service в конечном счёте достигают одинакового состояния документа. Максимальное время достижения консистентности: 3 секунды.                                                                                                                          |

---

## Функциональные требования

### Для AI-агентов:

1. **Получение текущей версии документа.** Агент отправляет `GET /api/document/current` в Text Service (через Load
   Balancer) и получает ответ `{version: number, text: string, timestamp: string}`.

2. **Генерация правки через ProxyAPI к OpenAI API.** Агент отправляет текст документа и свою инструкцию в
   `POST https://api.proxyapi.ru/openai/v1/responses` и получает предложение по изменению текста.

3. **Отправка правки на рассмотрение.** Агент отправляет `POST /api/edits` с телом
   `{agent_id: string, proposed_text: string, position: string, tokens_used: number}` и получает ответ
   `{edit_id: string, status: "accepted" | "rejected", version: number}` или `429 Too Many Requests` при превышении
   бюджета.

4. **Публикация информационных сообщений.** Агент отправляет `POST /api/chat/messages` с телом
   `{agent_id: string, message: string}` в Chat Service и получает ответ `{message_id: string, timestamp: string}`.

5. **Чтение истории сообщений других агентов.** Агент отправляет `GET /api/chat/messages?since=<timestamp>` в Chat
   Service и получает массив сообщений `[{agent_id: string, message: string, timestamp: string}, ...]`.

### Для Text Service:

6. **Предоставление текущей версии документа.** Text Service обрабатывает `GET /api/document/current` и возвращает
   последнюю версию из PostgreSQL: `{version: number, text: string, timestamp: string}`.

7. **Инициализация нового документа.** Text Service обрабатывает `POST /api/document/init` с телом
   `{topic: string, initial_text: string}` и создаёт запись документа с версией 1 в PostgreSQL.

8. **Приём правок от агентов.** Text Service обрабатывает `POST /api/edits` с телом
   `{agent_id: string, proposed_text: string, position: string, tokens_used: number}` и возвращает
   `{edit_id: string, status: string, version: number}`.

9. **Автоматическое применение правок.** Text Service проверяет отсутствие конфликтов (другие правки не изменили ту же
   позицию), применяет изменение к документу в транзакции PostgreSQL, создаёт новую версию документа и обновляет статус
   правки на "accepted".

10. **Хранение документа с версионностью.** Text Service сохраняет каждую версию документа в таблице `documents` с
    полями `{version: integer, text: text, timestamp: timestamptz, edit_id: uuid}`.

11. **Репликация изменений между узлами.** После применения правки Text Service отправляет `POST /api/replication/sync`
    с телом `{version: number, diff: string, timestamp: string, edit_id: string}` двум другим узлам и ожидает
    подтверждения `{status: "synced", version: number}`.

12. **Восстановление пропущенных изменений.** Text Service обрабатывает
    `GET /api/replication/catch-up?since_version=<number>` от восстановленного узла и возвращает массив пропущенных
    изменений `{versions: [{version: number, diff: string, timestamp: string}, ...]}`.

13. **Контроль бюджета токенов.** Text Service суммирует поле `tokens_used` из всех принятых правок в таблице
    `token_budget` и блокирует новые правки (возвращает `429 Too Many Requests`) при превышении лимита 15000 рублей (
    примерно 15 миллионов токенов GPT-4 Turbo).

14. **Отправка событий в Analytics Service.** После применения правки, успешной репликации или ошибки Text Service
    отправляет `POST /api/analytics/events` с телом
    `{event_type: string, agent_id: string, version: number, tokens: number, timestamp: string, metadata: object}`.

15. **Предоставление списка правок.** Text Service обрабатывает `GET /api/edits?limit=<number>&offset=<number>` и
    возвращает массив правок с пагинацией.

### Для Chat Service:

16. **Приём сообщений от агентов.** Chat Service обрабатывает `POST /api/chat/messages` с телом
    `{agent_id: string, message: string}`, сохраняет сообщение в Redis Streams и возвращает
    `{message_id: string, timestamp: string}`.

17. **Предоставление истории сообщений.** Chat Service обрабатывает
    `GET /api/chat/messages?since=<timestamp>&limit=<number>` и возвращает массив последних сообщений из Redis Streams:
    `[{agent_id: string, message: string, timestamp: string}, ...]`.

### Для Analytics Service:

18. **Приём событий от Text Service.** Analytics Service обрабатывает `POST /api/analytics/events` с телом
    `{event_type: string, agent_id: string, version: number, tokens: number, timestamp: string, metadata: object}`,
    сохраняет событие в PostgreSQL и возвращает `{status: "ok"}`.

19. **Агрегация и предоставление метрик.** Analytics Service обрабатывает
    `GET /api/analytics/metrics?period=<1h|24h|7d>` и возвращает агрегированные данные:
    `{total_edits: number, total_tokens: number, active_agents: number, avg_latency_ms: number, edits_per_minute: number, token_usage_by_time: [{timestamp: string, tokens: number}, ...]}`.

### Для Frontend (Next.js 15):

20. **Инициализация нового документа.** Пользователь заполняет форму (тема, начальный текст), фронтенд отправляет
    `POST /api/document/init` с телом `{topic: string, initial_text: string}` и получает
    `{document_id: string, status: "initialized"}`. После этого система автоматически запускает Docker-контейнеры с
    агентами.

21. **Просмотр текущего состояния документа.** Фронтенд периодически (каждые 2 секунды) отправляет
    `GET /api/document/current` и отображает полученный текст с подсветкой недавно изменённых фрагментов.

22. **Просмотр истории правок.** Фронтенд отправляет `GET /api/edits?limit=<number>&offset=<number>` и получает список
    правок для отображения в табличном виде с пагинацией.

23. **Просмотр чата агентов.** Фронтенд периодически (каждые 3 секунды) отправляет
    `GET /api/chat/messages?since=<last_timestamp>` и отображает новые сообщения в виде ленты.

24. **Отображение аналитики.** Фронтенд отправляет `GET /api/analytics/metrics?period=1h` и отображает графики (
    количество правок во времени, потребление токенов, количество активных агентов) с использованием библиотеки
    Recharts.

### Для Desktop Application (C++ Qt):

25. **Дублирование всей функциональности Frontend.** Desktop приложение реализует те же пять экранов (инициализация,
    просмотр документа, история правок, чат, аналитика) с использованием Qt Widgets, получая данные через те же REST API
    endpoints с помощью QNetworkAccessManager.

---

## Нефункциональные требования

- **Доступность:** система продолжает обрабатывать запросы агентов и клиентов при отказе одного из трёх узлов Text
  Service. Load Balancer перенаправляет трафик на работающие узлы в течение 5 секунд после обнаружения отказа.

- **Масштабируемость:** корректная работа при запуске от 5 до 50 агентов одновременно. При увеличении количества агентов
  среднее время обработки правки увеличивается линейно (не более чем в 2 раза при росте с 10 до 50 агентов).

- **Время отклика:**
    - Получение документа (`GET /api/document/current`): ≤ 500 мс в 95-м процентиле.
    - Применение правки (`POST /api/edits`) без учёта времени OpenAI API: ≤ 1 сек в 95-м процентиле.
    - Репликация между узлами: ≤ 3 сек до достижения eventual consistency.

- **Отказоустойчивость:**
    - Правки не теряются при падении агентов (agent retry логика с экспоненциальным backoff).
    - Правки не теряются при отказе одного узла Text Service (репликация на два других узла).
    - Восстановленный узел автоматически синхронизируется через `GET /api/replication/catch-up`.

- **Консистентность:**
    - Eventual consistency между узлами Text Service: все узлы достигают одинакового состояния в течение 3 секунд после
      применения правки.
    - Strong consistency внутри одного узла: использование транзакций PostgreSQL с уровнем изоляции READ COMMITTED.
    - Разрешение конфликтов при репликации: last-write-wins на основе timestamp.

- **Пропускная способность:** система обрабатывает минимум 10 правок в минуту при 20 активных агентах. При 50 агентах:
  минимум 20 правок в минуту.

- **Безопасность:**
    - Базовая аутентификация агентов через API-токены в заголовке `Authorization: Bearer <token>`.
    - Валидация всех входных данных (длина текста правки ≤ 10000 символов, корректность JSON).
    - Rate limiting: максимум 10 запросов в минуту от одного агента к Text Service.

- **Тестируемость:**
    - Автоматическое развёртывание системы в Docker Compose при push в ветку `main`.
    - Запуск интеграционных тестов в GitHub Actions с проверкой корректности полного цикла (агент → правка →
      репликация → аналитика).
    - Модульные тесты для критических компонентов (применение правок, репликация, разрешение конфликтов) с покрытием ≥
      70%.

---

## Ограничения на предметную область

1. **Язык документов:** только русский язык.

2. **Формат документа:** plain text без поддержки Markdown, HTML или других форматов разметки.

3. **LLM API:** используются разные модели от OpenAI без
   fine-tuning, дообучения. Заранее сказать актуальные модели на ноябрь-декабрь не представляется возможным.

4. **Типы правок:** поддерживается только замена существующего текста, добавление нового текста в конец или удаление
   фрагмента. Не поддерживается перестановка разделов или структурные изменения. Но, если агенты договорятся об этом в
   чате самостоятельно - это будет возможно. Необходимо тестировать.

5. **Количество документов:** система работает только с одним документом одновременно. Создание нового документа
   перезаписывает предыдущий.

6. **Количество узлов Text Service:** фиксированное количество — ровно три узла. Динамическое добавление или удаление
   узлов не поддерживается.

7. **Аутентификация:** упрощённая схема на основе статических API-токенов, переданных агентам при запуске. Отсутствует
   регистрация пользователей, OAuth или JWT.

8. **Персистентность Chat Service:** хранятся только последние 1000 сообщений в Redis Streams. Более старые сообщения
   автоматически удаляются (Redis MAXLEN).

9. **Обновление данных в реальном времени:** Frontend использует polling с интервалом 2-3 секунды вместо WebSocket или
   Server-Sent Events.

10. **Бюджет токенов:** жёсткий лимит в рублях (будет посчитано при тестировании, ориентировочно 15_000_000 токенов).
    При превышении все новые правки отклоняются с кодом 429. Пополнение бюджета возможно только через ручное изменение
    записи в базе данных (защита от выхода за рамки бюджета).

---

## Пользовательские сценарии

### Сценарий 1: Инициализация работы над документом

1. Пользователь открывает веб-интерфейс (Next.js Frontend) в браузере по адресу `https://p2p-chat.vitasha.ru/` (поддомен
   второго уровня на существующем личном домене Тим-лида). Далее по тексту вместо доменов используются локальные адреса.
2. На главной странице заполняет форму инициализации:
    - **Тема документа:** "История квантовых вычислений"
    - **Начальный текст:** "Квантовые вычисления — это область, изучающая использование квантовых явлений для обработки
      информации."
3. Нажимает кнопку "Начать работу".
4. Frontend отправляет запрос:
   ```
   POST http://localhost/api/document/init
   Content-Type: application/json
   
   {
     "topic": "История квантовых вычислений",
     "initial_text": "Квантовые вычисления — это область, изучающая использование квантовых явлений для обработки информации."
   }
   ```
5. Load Balancer перенаправляет запрос на один из узлов Text Service (например, узел A).
6. Text Service A создаёт запись в PostgreSQL:
   ```sql
   INSERT INTO documents (version, text, timestamp, edit_id)
   VALUES (1, 'Квантовые вычисления — это область...', NOW(), NULL);
   
   INSERT INTO token_budget (id, total_tokens, limit_tokens)
   VALUES (1, 0, 15000000)
   ON CONFLICT (id) DO UPDATE SET total_tokens = 0;
   ```
7. Text Service A возвращает ответ:
   ```
   201 Created
   {
     "document_id": "doc-abc-123",
     "status": "initialized",
     "version": 1
   }
   ```
8. Frontend получает ответ и перенаправляет пользователя на страницу `/document`.
9. Backend система (через docker-compose или оркестратор) автоматически запускает 10 Docker-контейнеров с AI-агентами,
   передавая каждому агенту конфигурацию через переменные окружения:
   ```
   AGENT_ROLE="Ты эксперт по квантовой физике. Добавляй технически точные детали."
   API_TOKEN="agent-token-001"
   TEXT_SERVICE_URL="http://load-balancer/api"
   CHAT_SERVICE_URL="http://load-balancer/api"
   OPENAI_API_KEY="sk-..."
   ```
10. Агенты начинают циклическую работу.

### Сценарий 2: Работа AI-агента (подробный цикл)

1. AI-агент (Docker-контейнер с Node.js 20) запускается и читает переменные окружения.
2. Агент входит в бесконечный цикл работы:

**Итерация цикла:**

3. **Шаг 1: Получение документа.**
    - Агент отправляет запрос:
      ```
      GET http://load-balancer/api/document/current
      Authorization: Bearer agent-token-001
      ```
    - Load Balancer перенаправляет запрос на Text Service B (по round-robin).
    - Text Service B выполняет SQL-запрос:
      ```sql
      SELECT version, text, timestamp
      FROM documents
      ORDER BY version DESC
      LIMIT 1;
      ```
    - PostgreSQL B возвращает:
      ```
      version: 5
      text: "Квантовые вычисления — это область... [текст 2000 символов]"
      timestamp: "2024-11-10T14:23:45Z"
      ```
    - Text Service B возвращает агенту:
      ```
      200 OK
      {
        "version": 5,
        "text": "Квантовые вычисления...",
        "timestamp": "2024-11-10T14:23:45Z"
      }
      ```

4. **Шаг 2: Генерация правки через OpenAI API.**
    - Агент формирует промпт для LLM:
      ```javascript
      const messages = [
        {
          role: "system",
          content: process.env.AGENT_ROLE
        },
        {
          role: "user",
          content: `Прочитай документ и предложи ОДНУ конкретную правку (добавление, удаление или замену текста). Укажи точную позицию изменения.\n\nДокумент:\n${documentText}`
        }
      ];
      ```
    - Агент отправляет запрос в OpenAI:
      ```
      POST https://api.openai.com/v1/chat/completions
      Authorization: Bearer sk-...
      Content-Type: application/json
      
      {
        "model": "gpt-4-turbo",
        "messages": [...],
        "temperature": 0.7,
        "max_tokens": 500
      }
      ```
    - OpenAI API возвращает:
      ```
      200 OK
      {
        "choices": [{
          "message": {
            "content": "Предлагаю добавить после второго абзаца:\n\n'Одним из ключевых принципов квантовых вычислений является суперпозиция — способность кубита находиться одновременно в состояниях |0⟩ и |1⟩.'\n\nПозиция: after_paragraph_2"
          }
        }],
        "usage": {
          "total_tokens": 450
        }
      }
      ```
    - Агент парсит ответ, извлекает текст правки, позицию и количество токенов.

5. **Шаг 3: Отправка правки в Text Service.**
    - Агент отправляет запрос:
      ```
      POST http://load-balancer/api/edits
      Authorization: Bearer agent-token-001
      Content-Type: application/json
      
      {
        "agent_id": "agent-physics-001",
        "proposed_text": "Одним из ключевых принципов квантовых вычислений является суперпозиция — способность кубита находиться одновременно в состояниях |0⟩ и |1⟩.",
        "position": "after_paragraph_2",
        "tokens_used": 450
      }
      ```
    - Load Balancer перенаправляет запрос на Text Service A.
    - Text Service A обрабатывает правку (подробности в Сценарии 3).
    - Text Service A возвращает агенту:
      ```
      201 Created
      {
        "edit_id": "edit-789",
        "status": "accepted",
        "version": 6
      }
      ```

6. **Шаг 4: Публикация сообщения в Chat Service.**
    - Агент отправляет запрос:
      ```
      POST http://load-balancer/api/chat/messages
      Authorization: Bearer agent-token-001
      Content-Type: application/json
      
      {
        "agent_id": "agent-physics-001",
        "message": "Добавил раздел о принципе суперпозиции (правка #edit-789)"
      }
      ```
    - Load Balancer перенаправляет запрос в Chat Service.
    - Chat Service сохраняет сообщение в Redis:
      ```
      XADD chat:messages MAXLEN ~ 1000 *
        agent_id agent-physics-001
        message "Добавил раздел о принципе суперпозиции (правка #edit-789)"
        timestamp 2024-11-10T14:24:12Z
      ```
    - Redis возвращает ID сообщения: `1699623852000-0`.
    - Chat Service возвращает агенту:
      ```
      200 OK
      {
        "message_id": "1699623852000-0",
        "timestamp": "2024-11-10T14:24:12Z"
      }
      ```

7. **Шаг 5: Ожидание перед следующей итерацией.**
    - Агент выполняет `await sleep(1000)` (ожидание 1 секунду).

8. **Шаг 6: Повторение цикла.**
    - Агент возвращается к Шагу 1 (получение документа).

**Обработка ошибок:**

- Если на Шаге 1 или 3 агент получает ошибку (timeout, 500, 503), он применяет retry логику с экспоненциальным backoff:
  ждёт 1 сек, затем 2 сек, затем 4 сек, до максимум 5 попыток.
- Если агент получает `429 Too Many Requests` (бюджет исчерпан), он логирует сообщение и завершает работу (выходит из
  цикла, контейнер останавливается).

### Сценарий 3: Обработка правки в Text Service (детальная транзакция)

1. Text Service A получает запрос `POST /api/edits` от агента через Load Balancer.
2. Text Service A валидирует запрос:
    - Проверяет наличие заголовка `Authorization` и корректность токена (сравнение с хранимым списком валидных токенов).
    - Проверяет корректность JSON-тела запроса.
    - Проверяет длину `proposed_text` (должна быть ≤ 10000 символов).
    - Проверяет, что `tokens_used` — положительное число.
3. Text Service A начинает транзакцию в PostgreSQL A:
   ```sql
   BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED;
   ```
4. **Проверка бюджета токенов:**
   ```sql
   SELECT total_tokens, limit_tokens
   FROM token_budget
   WHERE id = 1
   FOR UPDATE;
   -- Возвращает: total_tokens = 5430000, limit_tokens = 15000000
   ```
    - Text Service A вычисляет: `5430000 + 450 = 5430450` (в пределах лимита).

5. **Создание записи правки:**
   ```sql
   INSERT INTO edits (edit_id, agent_id, proposed_text, position, tokens_used, status, created_at)
   VALUES (gen_random_uuid(), 'agent-physics-001', 'Одним из ключевых принципов...', 'after_paragraph_2', 450, 'pending', NOW())
   RETURNING edit_id;
   -- Возвращает: edit_id = 'edit-789'
   ```

6. **Получение текущей версии документа:**
   ```sql
   SELECT version, text
   FROM documents
   ORDER BY version DESC
   LIMIT 1
   FOR UPDATE;
   -- Возвращает: version = 5, text = "Квантовые вычисления..."
   ```
    - Text Service A блокирует строку документа (FOR UPDATE) для предотвращения конкурентных изменений.

7. **Проверка конфликтов:**
    - Text Service A парсит `position: "after_paragraph_2"`.
    - Проверяет, что второй абзац всё ещё существует в тексте (разделители абзацев: `\n\n`).
    - Проверяет, что за последние 5 секунд не было других правок с той же позицией:
      ```sql
      SELECT COUNT(*) FROM edits
      WHERE position = 'after_paragraph_2'
        AND status = 'accepted'
        AND created_at > NOW() - INTERVAL '5 seconds';
      -- Возвращает: 0 (конфликтов нет)
      ```

8. **Применение правки к тексту:**
    - Text Service A находит позицию второго абзаца в тексте (индекс символа).
    - Вставляет `proposed_text` после второго абзаца.
    - Формирует новый текст документа.

9. **Создание новой версии документа:**
   ```sql
   INSERT INTO documents (version, text, timestamp, edit_id)
   VALUES (6, '[новый текст с правкой]', NOW(), 'edit-789');
   ```

10. **Обновление статуса правки:**
    ```sql
    UPDATE edits
    SET status = 'accepted'
    WHERE edit_id = 'edit-789';
    ```

11. **Обновление счётчика токенов:**
    ```sql
    UPDATE token_budget
    SET total_tokens = total_tokens + 450
    WHERE id = 1;
    ```

12. **Коммит транзакции:**
    ```sql
    COMMIT;
    ```

13. **Инициирование репликации (асинхронно, вне транзакции):**
    - Text Service A формирует репликационное сообщение:
      ```json
      {
        "version": 6,
        "diff": "INSERT at char_index 245: 'Одним из ключевых принципов...'",
        "timestamp": "2024-11-10T14:24:10.123Z",
        "edit_id": "edit-789",
        "full_text": "[полный текст документа версии 6]"
      }
      ```
    - Text Service A асинхронно (через asyncio.create_task) отправляет запросы:
      ```
      POST http://text-service-b:8000/api/replication/sync
      Content-Type: application/json
      
      {JSON сообщение выше}
      ```
      ```
      POST http://text-service-c:8000/api/replication/sync
      Content-Type: application/json
      
      {JSON сообщение выше}
      ```
    - Text Service A НЕ ЖДЁТ ответов от узлов B и C (eventual consistency).

14. **Отправка события в Analytics Service (асинхронно):**
    - Text Service A отправляет:
      ```
      POST http://analytics-service:8000/api/analytics/events
      Content-Type: application/json
      
      {
        "event_type": "edit_applied",
        "agent_id": "agent-physics-001",
        "version": 6,
        "tokens": 450,
        "timestamp": "2024-11-10T14:24:10.123Z",
        "metadata": {
          "edit_id": "edit-789",
          "node": "text-service-a",
          "position": "after_paragraph_2"
        }
      }
      ```

15. **Возврат ответа агенту:**
    ```
    201 Created
    Content-Type: application/json
    
    {
      "edit_id": "edit-789",
      "status": "accepted",
      "version": 6,
      "timestamp": "2024-11-10T14:24:10.123Z"
    }
    ```

**Если бюджет превышен (на Шаге 4):**

- Text Service A обнаруживает: `5430000 + 450000 = 5880000 > 15000000`.
- Text Service A выполняет `ROLLBACK;` (откат транзакции).
- Text Service A возвращает агенту:
  ```
  429 Too Many Requests
  Content-Type: application/json
  
  {
    "error": "Token budget exceeded",
    "used": 5430000,
    "limit": 15000000,
    "requested": 450000
  }
  ```

### Сценарий 4: Репликация между узлами Text Service

1. Text Service B (узел Санкт-Петербург) получает запрос от Text Service A:
   ```
   POST http://text-service-b:8000/api/replication/sync
   Content-Type: application/json
   
   {
     "version": 6,
     "diff": "INSERT at char_index 245: 'Одним из ключевых принципов...'",
     "timestamp": "2024-11-10T14:24:10.123Z",
     "edit_id": "edit-789",
     "full_text": "[полный текст документа версии 6]"
   }
   ```

2. Text Service B валидирует запрос (проверяет, что запрос исходит от доверенного узла — по IP или shared secret).

3. Text Service B начинает транзакцию в PostgreSQL B:
   ```sql
   BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED;
   ```

4. **Проверка текущей версии:**
   ```sql
   SELECT version, text
   FROM documents
   ORDER BY version DESC
   LIMIT 1
   FOR UPDATE;
   -- Возвращает: version = 5, text = "Квантовые вычисления..."
   ```

5. **Определение стратегии применения:**
    - Text Service B проверяет: `текущая_версия (5) + 1 == новая_версия (6)` → версии последовательны, можно применить
      diff.
    - Если бы версии не были последовательны (например, текущая версия 4, а приходит версия 6), Text Service B:
        - Откатывает транзакцию.
        - Отправляет запрос `GET /api/replication/catch-up?since_version=4` к узлу A.
        - Получает версии 5 и 6, применяет их последовательно.

6. **Применение изменения (используем full_text для упрощения):**
    - Text Service B может либо применить diff (вставка текста по индексу), либо использовать `full_text` из сообщения.
    - Для надёжности используем `full_text`:
   ```sql
   INSERT INTO documents (version, text, timestamp, edit_id)
   VALUES (6, '[полный текст из сообщения]', '2024-11-10T14:24:10.123Z', 'edit-789');
   ```

7. **Сохранение записи правки (если её нет):**
   ```sql
   INSERT INTO edits (edit_id, agent_id, proposed_text, position, tokens_used, status, created_at)
   VALUES ('edit-789', 'agent-physics-001', '...', 'after_paragraph_2', 450, 'accepted', '2024-11-10T14:24:10.123Z')
   ON CONFLICT (edit_id) DO NOTHING;
   ```

8. **Коммит транзакции:**
   ```sql
   COMMIT;
   ```

9. **Отправка подтверждения узлу A:**
   ```
   200 OK
   Content-Type: application/json
   
   {
     "status": "synced",
     "version": 6,
     "node": "text-service-b",
     "timestamp": "2024-11-10T14:24:11.456Z"
   }
   ```

10. **Отправка события в Analytics:**
    ```
    POST http://analytics-service:8000/api/analytics/events
    
    {
      "event_type": "replication_success",
      "version": 6,
      "timestamp": "2024-11-10T14:24:11.456Z",
      "metadata": {
        "source_node": "text-service-a",
        "target_node": "text-service-b",
        "latency_ms": 1333
      }
    }
    ```

11. Аналогичный процесс происходит на Text Service C (узел Новосибирск).

12. Через 1-2 секунды все три узла (A, B, C) имеют идентичную версию 6 документа. **Eventual consistency достигнута.**

### Сценарий 5: Отказ узла Text Service и восстановление

**Начальное состояние:**

- Text Service A, B, C работают, синхронизированы на версии 42.

**Отказ узла:**

1. В момент времени T0 Docker-контейнер Text Service B падает (команда `docker stop text-service-b` или OOM Killer
   завершает процесс).
2. Load Balancer продолжает направлять запросы по round-robin: треть запросов идёт на B.
3. Через 5 секунд (timeout) Load Balancer обнаруживает, что узел B не отвечает на health check `GET /health`.
4. Load Balancer помечает узел B как недоступный и исключает его из пула.
5. Теперь все запросы маршрутизируются только на узлы A и C.

**Работа без узла B:**

6. Агент отправляет правку: `POST http://load-balancer/api/edits`.
7. Load Balancer направляет запрос на узел A (или C).
8. Узел A применяет правку, создаёт версию 43.
9. Узел A пытается реплицировать на B и C:
    - `POST http://text-service-b:8000/api/replication/sync` → **Connection refused** (узел B недоступен).
    - `POST http://text-service-c:8000/api/replication/sync` → **200 OK** (узел C успешно применяет версию 43).
10. Узел A логирует ошибку репликации для узла B:
    ```
    ERROR: Failed to replicate version 43 to text-service-b: Connection refused
    ```
11. Узел A отправляет событие в Analytics:
    ```json
    {
      "event_type": "replication_failed",
      "version": 43,
      "timestamp": "...",
      "metadata": {
        "source_node": "text-service-a",
        "target_node": "text-service-b",
        "error": "Connection refused"
      }
    }
    ```
12. За следующие 5 минут применяются правки, версия на узлах A и C достигает 50. Узел B остаётся на версии 42.

**Восстановление узла B:**

13. Администратор или система мониторинга перезапускает контейнер: `docker start text-service-b`.
14. Text Service B запускается и выполняет процедуру startup:
    - Читает свою текущую версию из PostgreSQL B:
      ```sql
      SELECT version FROM documents ORDER BY version DESC LIMIT 1;
      -- Возвращает: 42
      ```
    - Отправляет запрос на один из других узлов (A или C) для определения актуальной версии:
      ```
      GET http://text-service-a:8000/api/document/current
      ```
    - Text Service A возвращает:
      ```json
      {
        "version": 50,
        "text": "...",
        "timestamp": "..."
      }
      ```
    - Text Service B обнаруживает отставание: `50 - 42 = 8 версий`.

15. Text Service B запрашивает пропущенные версии:
    ```
    GET http://text-service-a:8000/api/replication/catch-up?since_version=42
    ```

16. Text Service A выполняет запрос к PostgreSQL A:
    ```sql
    SELECT version, text, timestamp, edit_id
    FROM documents
    WHERE version > 42
    ORDER BY version ASC;
    -- Возвращает 8 строк (версии 43-50)
    ```

17. Text Service A формирует ответ:
    ```json
    200 OK
    {
      "versions": [
        {
          "version": 43,
          "full_text": "[текст версии 43]",
          "timestamp": "2024-11-10T14:25:00Z",
          "edit_id": "edit-790"
        },
        {
          "version": 44,
          "full_text": "[текст версии 44]",
          "timestamp": "2024-11-10T14:25:15Z",
          "edit_id": "edit-791"
        },
        ...
        {
          "version": 50,
          "full_text": "[текст версии 50]",
          "timestamp": "2024-11-10T14:30:00Z",
          "edit_id": "edit-797"
        }
      ]
    }
    ```

18. Text Service B последовательно применяет каждую версию в транзакциях PostgreSQL B:
    ```sql
    BEGIN;
    INSERT INTO documents (version, text, timestamp, edit_id)
    VALUES (43, '[текст версии 43]', '2024-11-10T14:25:00Z', 'edit-790');
    COMMIT;
    
    BEGIN;
    INSERT INTO documents (version, text, timestamp, edit_id)
    VALUES (44, '[текст версии 44]', '2024-11-10T14:25:15Z', 'edit-791');
    COMMIT;
    
    ... (повторяет для версий 45-50)
    ```

19. Text Service B логирует успешное восстановление:
    ```
    INFO: Successfully caught up from version 42 to 50. Applied 8 versions.
    ```

20. Text Service B отправляет событие в Analytics:
    ```json
    {
      "event_type": "node_recovered",
      "timestamp": "...",
      "metadata": {
        "node": "text-service-b",
        "from_version": 42,
        "to_version": 50,
        "versions_applied": 8
      }
    }
    ```

21. Text Service B возвращается в работу, начинает отвечать на `GET /health` с кодом 200.

22. Load Balancer обнаруживает, что узел B снова доступен (health check успешен), и добавляет его обратно в пул
    маршрутизации.

23. Система полностью восстановлена, все три узла (A, B, C) синхронизированы на версии 50.

### Сценарий 6: Исчерпание бюджета токенов

**Начальное состояние:**

- Применено 300 правок, суммарно использовано 14,950,000 токенов.
- Лимит бюджета: ~15,000,000 токенов.

**Приближение к лимиту:**

1. Агент отправляет правку с 30,000 токенов (большая правка — добавление целого раздела).
2. Text Service A обрабатывает правку:
    - Проверяет бюджет: `14,950,000 + 30,000 = 14,980,000` (в пределах лимита).
    - Применяет правку, создаёт версию 301.
    - Обновляет счётчик: `total_tokens = 14,980,000`.
3. Ещё 4 агента отправляют правки по 5,000 токенов каждая.
4. Text Service обрабатывает их последовательно:
    - Правка 1: `14,980,000 + 5,000 = 14,985,000` ✓
    - Правка 2: `14,985,000 + 5,000 = 14,990,000` ✓
    - Правка 3: `14,990,000 + 5,000 = 14,995,000` ✓
    - Правка 4: `14,995,000 + 5,000 = 15,000,000` ✓ (ровно на лимите)
5. Версия документа теперь 305, использовано ровно 15,000,000 токенов.

**Превышение лимита:**

6. Следующий агент отправляет правку с 500 токенов.
7. Text Service A обрабатывает запрос:
    - Начинает транзакцию.
    - Выполняет проверку бюджета:
      ```sql
      SELECT total_tokens, limit_tokens FROM token_budget WHERE id = 1 FOR UPDATE;
      -- Возвращает: total_tokens = 15000000, limit_tokens = 15000000
      ```
    - Вычисляет: `15,000,000 + 500 = 15,000,500 > 15,000,000` ❌
    - **Бюджет превышен!**
    - Выполняет `ROLLBACK;` (откатывает транзакцию, правка НЕ применяется).
8. Text Service A возвращает агенту:
   ```
   429 Too Many Requests
   Content-Type: application/json
   
   {
     "error": "Token budget exceeded",
     "used": 15000000,
     "limit": 15000000,
     "requested": 500,
     "message": "Cannot accept more edits. Budget limit reached."
   }
   ```
9. Text Service A отправляет событие в Analytics:
   ```json
   {
     "event_type": "budget_exceeded",
     "timestamp": "2024-11-10T15:00:00Z",
     "metadata": {
       "total_tokens": 15000000,
       "limit": 15000000,
       "rejected_tokens": 500,
       "agent_id": "agent-style-005"
     }
   }
   ```

**Остановка агентов:**

10. Агент получает 429, логирует сообщение:
    ```
    WARN: Token budget exceeded. Stopping agent. Used: 15,000,000 / 15,000,000
    ```
11. Агент завершает цикл работы и останавливается (exit code 0).
12. Все последующие агенты также получают 429 при попытке отправить правки.
13. В течение 1-2 минут все 10 агентов останавливаются.

**Уведомление пользователя:**

14. Frontend периодически запрашивает метрики: `GET /api/analytics/metrics?period=1h`.
15. Analytics Service возвращает данные, включая событие `budget_exceeded`:
    ```json
    {
      "total_edits": 305,
      "total_tokens": 15000000,
      "active_agents": 0,
      "budget_status": "exceeded",
      "last_edit_timestamp": "2024-11-10T14:59:45Z"
    }
    ```
16. Frontend обнаруживает `budget_status: "exceeded"` и отображает уведомление:
    ```
    ⚠️ Бюджет токенов исчерпан
    
    Работа агентов остановлена.
    Использовано: 15,000,000 токенов (~15,000 ₽)
    Финальная версия документа: 305
    
    [Кнопка: Скачать документ]
    ```
17. Пользователь может просмотреть финальный документ, экспортировать его в .txt файл, изучить статистику и историю
    правок.

### Сценарий 7: Просмотр прогресса пользователем (Frontend)

**Просмотр документа:**

1. Пользователь открывает страницу `http://localhost:3000/document`.
2. Frontend компонент React выполняет начальную загрузку данных при монтировании (useEffect):
   ```javascript
   useEffect(() => {
     fetchDocument();
     const interval = setInterval(fetchDocument, 2000); // Polling каждые 2 секунды
     return () => clearInterval(interval);
   }, []);
   
   const fetchDocument = async () => {
     const response = await fetch('http://localhost/api/document/current');
     const data = await response.json();
     setDocument(data);
   };
   ```
3. Frontend отправляет: `GET http://localhost/api/document/current`.
4. Load Balancer перенаправляет запрос на Text Service C.
5. Text Service C возвращает:
   ```json
   {
     "version": 87,
     "text": "[текст документа 15000 символов]",
     "timestamp": "2024-11-10T15:45:32Z"
   }
   ```
6. Frontend отображает текст в компоненте `<pre>` или `<div>` с форматированием.
7. Через 2 секунды Frontend повторяет запрос.
8. Text Service возвращает версию 88 (за 2 секунды была применена новая правка).
9. Frontend обнаруживает изменение версии (`87 !== 88`).
10. Frontend вычисляет diff между старым и новым текстом с помощью библиотеки (например, `diff` npm package).
11. Frontend подсвечивает изменённый фрагмент жёлтым цветом (`<span style="background: yellow;">`) на 5 секунд, затем
    убирает подсветку.

**Просмотр истории правок:**

12. Пользователь переходит на вкладку "История правок" (`/edits`).
13. Frontend отправляет: `GET http://localhost/api/edits?limit=50&offset=0`.
14. Text Service возвращает:
    ```json
    [
      {
        "edit_id": "edit-1234",
        "agent_id": "agent-physics-001",
        "status": "accepted",
        "proposed_text": "Суперпозиция позволяет кубиту находиться одновременно...",
        "position": "after_paragraph_2",
        "timestamp": "2024-11-10T15:44:12Z",
        "tokens_used": 450
      },
      {
        "edit_id": "edit-1235",
        "agent_id": "agent-style-002",
        "status": "accepted",
        "proposed_text": "Квантовая запутанность является другим фундаментальным явлением...",
        "position": "after_paragraph_5",
        "timestamp": "2024-11-10T15:44:25Z",
        "tokens_used": 380
      },
      ... (ещё 48 правок)
    ]
    ```
15. Frontend отображает таблицу с колонками:
    | ID правки | Агент | Статус | Фрагмент текста | Позиция | Время | Токены |
    |-----------|-------|--------|-----------------|---------|-------|--------|
    | edit-1234 | agent-physics-001 | ✓ Принята | Суперпозиция позволяет... | after_paragraph_2 | 15:44:12 | 450 |
    | edit-1235 | agent-style-002 | ✓ Принята | Квантовая запутанность... | after_paragraph_5 | 15:44:25 | 380 |
    | ... | ... | ... | ... | ... | ... | ... |
16. Пользователь может кликнуть "Загрузить ещё", что отправит `GET /api/edits?limit=50&offset=50` для следующей
    страницы.

**Просмотр чата агентов:**

17. Пользователь переходит на вкладку "Чат агентов" (`/chat`).
18. Frontend отправляет начальный запрос: `GET http://localhost/api/chat/messages?limit=50`.
19. Chat Service возвращает последние 50 сообщений из Redis Stream:
    ```json
    [
      {
        "agent_id": "agent-physics-001",
        "message": "Добавил раздел о суперпозиции (правка #edit-1234)",
        "timestamp": "2024-11-10T15:44:15Z"
      },
      {
        "agent_id": "agent-style-002",
        "message": "Исправил стилистику введения",
        "timestamp": "2024-11-10T15:44:20Z"
      },
      {
        "agent_id": "agent-facts-003",
        "message": "Проверил факты в разделе об истории — всё корректно",
        "timestamp": "2024-11-10T15:44:30Z"
      },
      ... (ещё 47 сообщений)
    ]
    ```
20. Frontend отображает ленту сообщений:
    ```
    [15:44:15] agent-physics-001: Добавил раздел о суперпозиции (правка #edit-1234)
    [15:44:20] agent-style-002: Исправил стилистику введения
    [15:44:30] agent-facts-003: Проверил факты в разделе об истории — всё корректно
    ...
    ```
21. Frontend запускает polling (каждые 3 секунды):
    ```javascript
    const fetchMessages = async () => {
      const lastTimestamp = messages[messages.length - 1]?.timestamp || '1970-01-01T00:00:00Z';
      const response = await fetch(`http://localhost/api/chat/messages?since=${lastTimestamp}&limit=10`);
      const newMessages = await response.json();
      if (newMessages.length > 0) {
        setMessages(prev => [...prev, ...newMessages]);
        scrollToBottom(); // Автопрокрутка к последнему сообщению
      }
    };
    ```

**Просмотр аналитики:**

22. Пользователь переходит на вкладку "Аналитика" (`/analytics`).
23. Frontend отправляет: `GET http://localhost/api/analytics/metrics?period=1h`.
24. Analytics Service выполняет агрегирующие запросы в PostgreSQL:
    ```sql
    -- Общее количество правок за последний час
    SELECT COUNT(*) FROM events
    WHERE event_type = 'edit_applied'
      AND timestamp > NOW() - INTERVAL '1 hour';
    -- Возвращает: 87
    
    -- Суммарное количество токенов за последний час
    SELECT SUM(tokens) FROM events
    WHERE event_type = 'edit_applied'
      AND timestamp > NOW() - INTERVAL '1 hour';
    -- Возвращает: 42500
    
    -- Количество уникальных активных агентов за последние 5 минут
    SELECT COUNT(DISTINCT agent_id) FROM events
    WHERE timestamp > NOW() - INTERVAL '5 minutes';
    -- Возвращает: 8
    
    -- Средняя латентность репликации
    SELECT AVG((metadata->>'latency_ms')::int) FROM events
    WHERE event_type = 'replication_success'
      AND timestamp > NOW() - INTERVAL '1 hour';
    -- Возвращает: 320
    
    -- Количество правок в минуту (time-series для графика)
    SELECT
      date_trunc('minute', timestamp) AS bucket,
      COUNT(*) AS edits_count
    FROM events
    WHERE event_type = 'edit_applied'
      AND timestamp > NOW() - INTERVAL '1 hour'
    GROUP BY bucket
    ORDER BY bucket ASC;
    -- Возвращает 60 строк (по одной на каждую минуту последнего часа)
    
    -- Потребление токенов во времени (time-series для графика)
    SELECT
      date_trunc('minute', timestamp) AS bucket,
      SUM(tokens) AS tokens_sum
    FROM events
    WHERE event_type = 'edit_applied'
      AND timestamp > NOW() - INTERVAL '1 hour'
    GROUP BY bucket
    ORDER BY bucket ASC;
    -- Возвращает 60 строк
    ```
25. Analytics Service возвращает:
    ```json
    {
      "total_edits": 87,
      "total_tokens": 42500,
      "active_agents": 8,
      "avg_latency_ms": 320,
      "edits_per_minute": 1.45,
      "token_usage_by_time": [
        {"timestamp": "2024-11-10T15:00:00Z", "tokens": 1200},
        {"timestamp": "2024-11-10T15:01:00Z", "tokens": 1450},
        {"timestamp": "2024-11-10T15:02:00Z", "tokens": 980},
        ... (58 записей)