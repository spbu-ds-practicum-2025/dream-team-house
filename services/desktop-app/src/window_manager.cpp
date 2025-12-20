#include "window_manager.h"

#include <QWidget>

#include "analytics_window.h"
#include "api_client.h"
#include "chat_window.h"
#include "document_window.h"
#include "edits_window.h"
#include "init_document_window.h"
#include "main_window.h"
#include "session_state.h"
#include "settings_window.h"

WindowManager::WindowManager(ApiClient* apiClient, SessionState* state, QObject* parent)
    : QObject(parent)
    , m_apiClient(apiClient)
    , m_state(state)
{
}

void WindowManager::setMainWindow(MainWindow* window)
{
    m_mainWindow = window;
    connectWindowLifecycle(window, WindowType::Main);
}

QWidget* WindowManager::ensureWindow(WindowType type)
{
    switch (type) {
    case WindowType::Main:
        if (!m_mainWindow) {
            m_mainWindow = new MainWindow(this);
            connectWindowLifecycle(m_mainWindow, type);
        }
        return m_mainWindow;
    case WindowType::Init:
        if (!m_initWindow) {
            m_initWindow = new InitDocumentWindow(this, m_apiClient, m_state);
            connectWindowLifecycle(m_initWindow, type);
        }
        return m_initWindow;
    case WindowType::Document:
        if (!m_documentWindow) {
            m_documentWindow = new DocumentWindow(this, m_apiClient, m_state);
            connectWindowLifecycle(m_documentWindow, type);
        }
        return m_documentWindow;
    case WindowType::Edits:
        if (!m_editsWindow) {
            m_editsWindow = new EditsWindow(this, m_apiClient, m_state);
            connectWindowLifecycle(m_editsWindow, type);
        }
        return m_editsWindow;
    case WindowType::Chat:
        if (!m_chatWindow) {
            m_chatWindow = new ChatWindow(this, m_apiClient, m_state);
            connectWindowLifecycle(m_chatWindow, type);
        }
        return m_chatWindow;
    case WindowType::Analytics:
        if (!m_analyticsWindow) {
            m_analyticsWindow = new AnalyticsWindow(this, m_apiClient, m_state);
            connectWindowLifecycle(m_analyticsWindow, type);
        }
        return m_analyticsWindow;
    case WindowType::Settings:
        if (!m_settingsWindow) {
            m_settingsWindow = new SettingsWindow(this, m_apiClient, m_state);
            connectWindowLifecycle(m_settingsWindow, type);
        }
        return m_settingsWindow;
    default:
        return nullptr;
    }
    return nullptr;
}

void WindowManager::showOrActivate(WindowType type)
{
    QWidget* window = ensureWindow(type);
    if (!window) {
        return;
    }
    window->show();
    window->raise();
    window->activateWindow();
}

void WindowManager::connectWindowLifecycle(QWidget* widget, WindowType type)
{
    if (!widget) {
        return;
    }
    connect(widget, &QObject::destroyed, this, [this, type]() {
        switch (type) {
        case WindowType::Main:
            m_mainWindow = nullptr;
            break;
        case WindowType::Init:
            m_initWindow = nullptr;
            break;
        case WindowType::Document:
            m_documentWindow = nullptr;
            break;
        case WindowType::Edits:
            m_editsWindow = nullptr;
            break;
        case WindowType::Chat:
            m_chatWindow = nullptr;
            break;
        case WindowType::Analytics:
            m_analyticsWindow = nullptr;
            break;
        case WindowType::Settings:
            m_settingsWindow = nullptr;
            break;
        }
    });
}
