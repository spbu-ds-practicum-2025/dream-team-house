#pragma once

#include <QMainWindow>

class ApiClient;
class NavigationBar;
class SessionState;
class WindowManager;
class QLabel;
class QTableWidget;
class QPushButton;

class EditsWindow : public QMainWindow {
    Q_OBJECT
public:
    EditsWindow(WindowManager* manager, ApiClient* client, SessionState* state, QWidget* parent = nullptr);

private slots:
    void refreshEdits();
    void nextPage();
    void prevPage();

private:
    void setupUi();
    void populateTable(const QJsonArray& items);

    WindowManager* m_manager;
    ApiClient* m_client;
    SessionState* m_state;
    QTableWidget* m_table;
    QLabel* m_statusLabel;
    QPushButton* m_prevButton;
    QPushButton* m_nextButton;
    int m_offset;
    int m_limit;
};
