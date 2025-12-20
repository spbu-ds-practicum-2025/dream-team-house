#pragma once

#include <QMainWindow>

#include "app_config.h"
#include "window_manager.h"

class QLabel;
class QPushButton;
class SessionState;

class MainWindow : public QMainWindow {
    Q_OBJECT
public:
    explicit MainWindow(WindowManager* manager, QWidget* parent = nullptr);

private slots:
    void refreshState();

private:
    void setupUi();

    WindowManager* m_manager;
    SessionState* m_state;
    QLabel* m_documentIdLabel;
    QLabel* m_versionLabel;
    QLabel* m_urlsLabel;
};
