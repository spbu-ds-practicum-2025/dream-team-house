#pragma once

#include <QMainWindow>

class ApiClient;
class NavigationBar;
class SessionState;
class WindowManager;
class QLabel;
class QPushButton;
class QCheckBox;

class SettingsWindow : public QMainWindow {
    Q_OBJECT
public:
    SettingsWindow(WindowManager* manager, ApiClient* client, SessionState* state, QWidget* parent = nullptr);

private slots:
    void copyDiagnostics();
    void toggleDarkTheme(bool enabled);

private:
    void setupUi();
    QString diagnosticsText() const;

    WindowManager* m_manager;
    ApiClient* m_client;
    SessionState* m_state;
    QLabel* m_infoLabel;
    QPushButton* m_copyButton;
    QCheckBox* m_darkTheme;
};
