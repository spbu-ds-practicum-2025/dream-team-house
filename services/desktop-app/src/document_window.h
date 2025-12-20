#pragma once

#include <QMainWindow>
#include <QTimer>

class ApiClient;
class NavigationBar;
class SessionState;
class WindowManager;
class QLabel;
class QTextBrowser;
class QPushButton;

class DocumentWindow : public QMainWindow {
    Q_OBJECT
public:
    DocumentWindow(WindowManager* manager, ApiClient* client, SessionState* state, QWidget* parent = nullptr);
    ~DocumentWindow() override;

private slots:
    void refreshDocument();

private:
    void setupUi();
    void startTimer();

    WindowManager* m_manager;
    ApiClient* m_client;
    SessionState* m_state;
    QTextBrowser* m_textView;
    QLabel* m_metaLabel;
    QLabel* m_errorLabel;
    QPushButton* m_refreshButton;
    QTimer m_timer;
};
