#include "analytics_window.h"

#include <QComboBox>
#include <QJsonArray>
#include <QJsonObject>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QStatusBar>
#include <QTableWidget>
#include <QTableWidgetItem>
#include <QVBoxLayout>
#include <QWidget>
#include <QtCharts/QBarSet>
#include <QtCharts/QChart>
#include <QtCharts/QChartView>
#include <QtCharts/QLineSeries>
#include <QtCharts/QValueAxis>

#include "api_client.h"
#include "navigation_bar.h"
#include "session_state.h"
#include "window_manager.h"

using namespace QtCharts;

AnalyticsWindow::AnalyticsWindow(WindowManager* manager, ApiClient* client, SessionState* state, QWidget* parent)
    : QMainWindow(parent)
    , m_manager(manager)
    , m_client(client)
    , m_state(state)
    , m_statusLabel(nullptr)
    , m_periodCombo(nullptr)
    , m_table(nullptr)
    , m_chartView(nullptr)
    , m_refreshButton(nullptr)
{
    setupUi();
    refreshMetrics();
}

void AnalyticsWindow::setupUi()
{
    setWindowTitle(tr("Analytics"));
    resize(720, 520);

    auto* central = new QWidget(this);
    auto* layout = new QVBoxLayout(central);
    layout->setContentsMargins(12, 12, 12, 12);
    layout->setSpacing(8);

    layout->addWidget(new NavigationBar(m_manager, this));

    auto* controls = new QHBoxLayout();
    m_periodCombo = new QComboBox(this);
    m_periodCombo->addItems({QStringLiteral("1h"), QStringLiteral("24h"), QStringLiteral("7d")});
    controls->addWidget(new QLabel(tr("Period:"), this));
    controls->addWidget(m_periodCombo);
    m_refreshButton = new QPushButton(tr("Refresh"), this);
    controls->addWidget(m_refreshButton);
    controls->addStretch();
    layout->addLayout(controls);

    m_table = new QTableWidget(this);
    m_table->setColumnCount(2);
    m_table->setHorizontalHeaderLabels({tr("Metric"), tr("Value")});
    layout->addWidget(m_table);

    m_chartView = new QChartView(new QChart(), this);
    m_chartView->setMinimumHeight(200);
    layout->addWidget(m_chartView);

    m_statusLabel = new QLabel(this);
    layout->addWidget(m_statusLabel);

    connect(m_refreshButton, &QPushButton::clicked, this, &AnalyticsWindow::refreshMetrics);

    setCentralWidget(central);
    statusBar()->showMessage(tr("Analytics metrics"));
}

void AnalyticsWindow::updateChart(const QJsonArray& points)
{
    auto* chart = new QChart();
    auto* series = new QLineSeries(chart);
    series->setName(tr("Token usage"));
    for (const auto& value : points) {
        const auto obj = value.toObject();
        const auto ts = obj.value("timestamp").toString();
        const auto val = obj.value("value").toDouble();
        series->append(series->count(), val);
    }
    chart->addSeries(series);
    chart->createDefaultAxes();
    chart->setTitle(tr("Token usage over time"));
    m_chartView->setChart(chart);
}

void AnalyticsWindow::refreshMetrics()
{
    if (!m_client) {
        return;
    }
    const QString period = m_periodCombo->currentText();
    m_statusLabel->setText(tr("Loading metrics..."));
    m_client->fetchAnalytics(period, [this](bool ok, const QJsonObject& obj, const QString& err) {
        if (!ok) {
            m_statusLabel->setText(tr("Failed: %1").arg(err));
            return;
        }
        struct Metric {
            QString name;
            QString key;
        };
        const QList<Metric> metrics = {
            {tr("Total edits"), "total_edits"},
            {tr("Total tokens"), "total_tokens"},
            {tr("Active agents"), "active_agents"},
            {tr("Avg latency, ms"), "avg_latency_ms"},
            {tr("Edits per minute"), "edits_per_minute"},
        };
        m_table->setRowCount(metrics.size());
        int row = 0;
        for (const auto& metric : metrics) {
            m_table->setItem(row, 0, new QTableWidgetItem(metric.name));
            m_table->setItem(row, 1, new QTableWidgetItem(QString::number(obj.value(metric.key).toDouble())));
            ++row;
        }
        updateChart(obj.value("token_usage_by_time").toArray());
        m_statusLabel->setText(tr("Updated"));
    });
}
