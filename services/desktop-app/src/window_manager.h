#pragma once

#include <QObject>
#include <QPointer>

class ApiClient;
class SessionState;
class MainWindow;
class InitDocumentWindow;
class DocumentWindow;
class EditsWindow;
class ChatWindow;
class AnalyticsWindow;
class SettingsWindow;

enum class WindowType {
    Main,
    Init,
    Document,
    Edits,
    Chat,
    Analytics,
    Settings,
};

class WindowManager : public QObject {
    Q_OBJECT
public:
    WindowManager(ApiClient* apiClient, SessionState* state, QObject* parent = nullptr);

    void showOrActivate(WindowType type);
    void setMainWindow(MainWindow* window);

    ApiClient* api() const { return m_apiClient; }
    SessionState* state() const { return m_state; }

private:
    QWidget* ensureWindow(WindowType type);
    void connectWindowLifecycle(QWidget* widget, WindowType type);

    ApiClient* m_apiClient;
    SessionState* m_state;

    QPointer<MainWindow> m_mainWindow;
    QPointer<InitDocumentWindow> m_initWindow;
    QPointer<DocumentWindow> m_documentWindow;
    QPointer<EditsWindow> m_editsWindow;
    QPointer<ChatWindow> m_chatWindow;
    QPointer<AnalyticsWindow> m_analyticsWindow;
    QPointer<SettingsWindow> m_settingsWindow;
};
