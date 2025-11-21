# Load Balancer

## Описание

Nginx-based load balancer для распределения HTTP-запросов между тремя узлами Text Service и проксирования запросов к
Chat Service и Analytics Service.

## Технологии

- Nginx 1.25
- Docker

## Архитектура

### Upstream серверы

#### Text Service (Round-robin)

Три узла с автоматическим health checking:

- `text-service-a:8000` (Москва)
- `text-service-b:8000` (Санкт-Петербург)
- `text-service-c:8000` (Новосибирск)

#### Chat Service (Прямое проксирование)

- `chat-service:8000`

#### Analytics Service (Прямое проксирование)

- `analytics-service:8000`

## Конфигурация Nginx

```nginx
upstream text_service {
    # Round-robin load balancing
    server text-service-a:8000 max_fails=3 fail_timeout=60s;
    server text-service-b:8000 max_fails=3 fail_timeout=60s;
    server text-service-c:8000 max_fails=3 fail_timeout=60s;
}

upstream chat_service {
    server chat-service:8000;
}

upstream analytics_service {
    server analytics-service:8000;
}

server {
    listen 80;
    server_name _;

    # Text Service endpoints
    location /api/document/ {
        proxy_pass http://text_service;
        proxy_next_upstream error timeout http_500 http_502 http_503 http_504;
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
    }

    location /api/edits {
        proxy_pass http://text_service;
        proxy_next_upstream error timeout http_500 http_502 http_503 http_504;
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
    }

    location /api/replication/ {
        proxy_pass http://text_service;
        proxy_next_upstream error timeout http_500 http_502 http_503 http_504;
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
    }

    # Chat Service endpoints
    location /api/chat/ {
        proxy_pass http://chat_service;
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
    }

    # Analytics Service endpoints
    location /api/analytics/ {
        proxy_pass http://analytics_service;
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

## Health Checking

### Параметры

- **Интервал проверки**: каждые 10 секунд
- **Timeout**: 5 секунд
- **Max fails**: 3 неудачные попытки
- **Fail timeout**: исключение узла на 60 секунд

### Механизм работы

1. Nginx отправляет `GET /health` каждому узлу Text Service
2. Если узел не отвечает или возвращает статус ≠ 200:
    - Увеличивается счётчик неудач
    - При достижении `max_fails=3` узел исключается на 60 секунд
3. По истечении `fail_timeout` узел снова включается в пул
4. Если узел отвечает успешно, счётчик неудач сбрасывается

## Отказоустойчивость

### Proxy Next Upstream

Автоматическая переадресация на другой узел при:

- Ошибке соединения (`error`)
- Таймауте (`timeout`)
- HTTP статусах: 500, 502, 503, 504

### Пример сценария отказа

1. Узел B падает (Docker stop)
2. Load Balancer обнаруживает отказ через health check (≤10 секунд)
3. Новые запросы направляются только на узлы A и C
4. Узел B восстанавливается (Docker start)
5. После успешного health check узел B возвращается в пул

## Алгоритм балансировки

### Round-robin (по умолчанию)

- Циклическое распределение запросов между узлами
- Равномерная нагрузка при одинаковой производительности узлов
- Простота конфигурации

### Альтернативы (для будущего расширения)

- `least_conn` - направление на узел с наименьшим числом активных соединений
- `ip_hash` - привязка клиента к одному узлу (sticky sessions)
- `random` - случайное распределение

## Логирование

### Access Log

```nginx
log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                '$status $body_bytes_sent "$http_referer" '
                '"$http_user_agent" "$http_x_forwarded_for" '
                'upstream: $upstream_addr upstream_status: $upstream_status';

access_log /var/log/nginx/access.log main;
```

### Error Log

```nginx
error_log /var/log/nginx/error.log warn;
```

## Мониторинг

### Метрики для отслеживания

- Количество запросов на каждый upstream
- Время отклика каждого узла
- Количество отказов (5xx ошибок)
- Частота переключения между узлами

### Интеграция с аналитикой

- Отправка логов в Analytics Service (опционально)
- Экспорт метрик для внешних систем мониторинга

## Docker Integration

### Dockerfile

```dockerfile
FROM nginx:1.25-alpine
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Docker Compose

```yaml
load-balancer:
  image: nginx:1.25-alpine
  ports:
    - "80:80"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf:ro
  depends_on:
    - text-service-a
    - text-service-b
    - text-service-c
    - chat-service
    - analytics-service
```

## Требования

- Nginx 1.25+
- Docker 24+
- Сетевое соединение с upstream серверами
