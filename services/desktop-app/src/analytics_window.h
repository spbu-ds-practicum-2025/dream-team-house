#pragma once

#include <QMainWindow>

#include <QtCharts/QChartView>
#include <QtCharts/QLineSeries>
#include <QtCharts/QChart>

class ApiClient;
class NavigationBar;
class SessionState;
class WindowManager;
class QLabel;
class QComboBox;
class QPushButton;
class QTableWidget;

class AnalyticsWindow : public QMainWindow {
    Q_OBJECT
public:
    AnalyticsWindow(WindowManager* manager, ApiClient* client, SessionState* state, QWidget* parent = nullptr);

private slots:
    void refreshMetrics();

private:
    void setupUi();
    void updateChart(const QJsonArray& points);

    WindowManager* m_manager;
    ApiClient* m_client;
    SessionState* m_state;
    QLabel* m_statusLabel;
    QComboBox* m_periodCombo;
    QTableWidget* m_table;
    QtCharts::QChartView* m_chartView;
    QPushButton* m_refreshButton;
};
