#pragma once

#include <QMainWindow>
#include <QTimer>
#include <QJsonArray>

class ApiClient;
class NavigationBar;
class SessionState;
class WindowManager;
class QListWidget;
class QLabel;
class QPushButton;
class QLineEdit;

class ChatWindow : public QMainWindow {
    Q_OBJECT
public:
    ChatWindow(WindowManager* manager, ApiClient* client, SessionState* state, QWidget* parent = nullptr);
    ~ChatWindow() override;

private slots:
    void refreshChat();
    void applyFilter();

private:
    void setupUi();
    void startTimer();
    void appendMessages(const QJsonArray& arr);

    WindowManager* m_manager;
    ApiClient* m_client;
    SessionState* m_state;
    QListWidget* m_list;
    QLabel* m_statusLabel;
    QLineEdit* m_filterEdit;
    QPushButton* m_refreshButton;
    QTimer m_timer;
};
