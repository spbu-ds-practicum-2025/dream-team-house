#pragma once

#include <QMainWindow>

class ApiClient;
class NavigationBar;
class SessionState;
class WindowManager;
class QLabel;
class QLineEdit;
class QTextEdit;
class QPushButton;

class InitDocumentWindow : public QMainWindow {
    Q_OBJECT
public:
    InitDocumentWindow(WindowManager* manager, ApiClient* client, SessionState* state, QWidget* parent = nullptr);

private slots:
    void handleInit();

private:
    void setupUi();

    WindowManager* m_manager;
    ApiClient* m_client;
    SessionState* m_state;
    QLineEdit* m_topicEdit;
    QTextEdit* m_initialTextEdit;
    QLabel* m_statusLabel;
    QPushButton* m_initButton;
};
