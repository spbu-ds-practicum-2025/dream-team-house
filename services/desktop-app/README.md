# Desktop Application

## Описание

Нативное кроссплатформенное приложение на C++ с Qt 6, дублирующее всю функциональность веб-интерфейса. Обеспечивает
работу с системой через десктопное приложение с использованием тех же REST API endpoints.

## Технологии

- C++ 17
- Qt 6.5
- Qt Widgets (GUI)
- Qt Network (HTTP клиент)
- Qt Charts (визуализация графиков)
- CMake (система сборки)

## Архитектура

### Основное окно (QMainWindow)

- QTabWidget с пятью вкладками
- QMenuBar с основными действиями
- QStatusBar для отображения статуса соединения

### Вкладки приложения

#### 1. Инициализация

Виджеты:

- QLineEdit для темы документа
- QTextEdit для начального текста
- QPushButton "Начать работу"
- Запрос: `POST /api/document/init`

#### 2. Документ

Виджеты:

- QTextBrowser для отображения документа (read-only)
- QLabel для версии и timestamp
- QTimer (2 секунды) для автообновления
- Запрос: `GET /api/document/current`

#### 3. Правки

Виджеты:

- QTableView с моделью для отображения правок
- Столбцы: ID, Агент, Статус, Токены, Время
- QPushButton для пагинации (Назад/Вперёд)
- Запрос: `GET /api/edits?limit=<number>&offset=<number>`

#### 4. Чат

Виджеты:

- QListWidget для отображения сообщений
- QTimer (3 секунды) для автообновления
- Автопрокрутка к новым сообщениям
- Запрос: `GET /api/chat/messages?since=<last_timestamp>`

#### 5. Аналитика

Виджеты:

- QChartView с QLineSeries (график токенов во времени)
- QBarSeries (правки в минуту)
- QLabel для числовых метрик
- QComboBox для выбора периода (1h/24h/7d)
- QPushButton "Обновить"
- Запрос: `GET /api/analytics/metrics?period=<period>`

## HTTP клиент (Qt Network)

### QNetworkAccessManager

```cpp
QNetworkAccessManager *manager = new QNetworkAccessManager(this);
QNetworkRequest request(QUrl("http://load-balancer/api/document/current"));
QNetworkReply *reply = manager->get(request);

connect(reply, &QNetworkReply::finished, this, [reply]() {
    if (reply->error() == QNetworkReply::NoError) {
        QByteArray data = reply->readAll();
        QJsonDocument doc = QJsonDocument::fromJson(data);
        // Обработка данных
    }
    reply->deleteLater();
});
```

## Визуализация графиков (Qt Charts)

### Линейный график токенов

```cpp
QLineSeries *series = new QLineSeries();
series->append(timestamp1, tokens1);
series->append(timestamp2, tokens2);

QChart *chart = new QChart();
chart->addSeries(series);
chart->setTitle("Token Usage Over Time");

QChartView *chartView = new QChartView(chart);
```

## Сборка

### CMake конфигурация

```cmake
cmake_minimum_required(VERSION 3.16)
project(dream-team-desktop VERSION 1.0.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(Qt6 REQUIRED COMPONENTS Widgets Network Charts)

add_executable(dream-team-desktop
    src/main.cpp
    src/mainwindow.cpp
    src/mainwindow.h
)

target_link_libraries(dream-team-desktop
    Qt6::Widgets
    Qt6::Network
    Qt6::Charts
)
```

### Сборка для разных платформ

- **Linux**: `cmake -B build && cmake --build build`
- **Windows**: CMake + Visual Studio или MinGW
- **macOS**: CMake + Xcode

## Особенности реализации

### Автообновление данных

- QTimer для периодических запросов
- Отмена таймеров при закрытии вкладок
- Обработка ошибок сети с повторными попытками

### Парсинг JSON

```cpp
QJsonDocument doc = QJsonDocument::fromJson(data);
QJsonObject obj = doc.object();
QString version = obj["version"].toString();
QString text = obj["text"].toString();
```

### Обработка ошибок

- Отображение QMessageBox при ошибках сети
- Индикатор состояния соединения в QStatusBar
- Retry логика с экспоненциальным backoff

### Стилизация

- Нативный внешний вид для каждой платформы
- Опциональная кастомная стилизация через QSS (Qt Style Sheets)
- Поддержка тёмной темы через системные настройки

## Дистрибуция

### Статическая линковка Qt

- Упрощение дистрибуции (один исполняемый файл)
- Отсутствие зависимостей от установленных библиотек Qt

### Установщики

- **Linux**: AppImage или .deb/.rpm пакеты
- **Windows**: NSIS или Inno Setup
- **macOS**: .dmg с drag-and-drop установкой

## Требования

- Qt 6.5+
- CMake 3.16+
- C++17 совместимый компилятор
    - GCC 7+ (Linux)
    - MSVC 2019+ (Windows)
    - Clang 10+ (macOS)
