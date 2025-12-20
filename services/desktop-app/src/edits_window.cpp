#include "edits_window.h"

#include <QHeaderView>
#include <QHBoxLayout>
#include <QJsonArray>
#include <QJsonObject>
#include <QLabel>
#include <QPushButton>
#include <QStatusBar>
#include <QTableWidget>
#include <QTableWidgetItem>
#include <QVBoxLayout>
#include <QWidget>

#include <QtGlobal>

#include "api_client.h"
#include "navigation_bar.h"
#include "session_state.h"
#include "window_manager.h"

EditsWindow::EditsWindow(WindowManager* manager, ApiClient* client, SessionState* state, QWidget* parent)
    : QMainWindow(parent)
    , m_manager(manager)
    , m_client(client)
    , m_state(state)
    , m_table(nullptr)
    , m_statusLabel(nullptr)
    , m_prevButton(nullptr)
    , m_nextButton(nullptr)
    , m_offset(0)
    , m_limit(20)
{
    setupUi();
    refreshEdits();
}

void EditsWindow::setupUi()
{
    setWindowTitle(tr("Edits"));
    resize(720, 480);

    auto* central = new QWidget(this);
    auto* layout = new QVBoxLayout(central);
    layout->setContentsMargins(12, 12, 12, 12);
    layout->setSpacing(8);

    layout->addWidget(new NavigationBar(m_manager, this));

    m_table = new QTableWidget(this);
    m_table->setColumnCount(6);
    m_table->setHorizontalHeaderLabels({tr("Edit ID"), tr("Agent"), tr("Op"), tr("Status"), tr("Tokens"), tr("Created")});
    m_table->horizontalHeader()->setStretchLastSection(true);
    layout->addWidget(m_table, 1);

    m_statusLabel = new QLabel(this);
    layout->addWidget(m_statusLabel);

    auto* buttons = new QHBoxLayout();
    m_prevButton = new QPushButton(tr("Prev"), this);
    m_nextButton = new QPushButton(tr("Next"), this);
    buttons->addWidget(m_prevButton);
    buttons->addWidget(m_nextButton);
    buttons->addStretch();
    layout->addLayout(buttons);

    connect(m_prevButton, &QPushButton::clicked, this, &EditsWindow::prevPage);
    connect(m_nextButton, &QPushButton::clicked, this, &EditsWindow::nextPage);

    setCentralWidget(central);
    statusBar()->showMessage(tr("Paginated edits"));
}

void EditsWindow::populateTable(const QJsonArray& items)
{
    m_table->setRowCount(items.size());
    int row = 0;
    for (const auto& value : items) {
        const auto obj = value.toObject();
        m_table->setItem(row, 0, new QTableWidgetItem(obj.value("edit_id").toString()));
        m_table->setItem(row, 1, new QTableWidgetItem(obj.value("agent_id").toString()));
        m_table->setItem(row, 2, new QTableWidgetItem(obj.value("operation").toString()));
        m_table->setItem(row, 3, new QTableWidgetItem(obj.value("status").toString()));
        m_table->setItem(row, 4, new QTableWidgetItem(QString::number(obj.value("tokens_used").toInt())));
        m_table->setItem(row, 5, new QTableWidgetItem(obj.value("created_at").toString()));
        ++row;
    }
}

void EditsWindow::refreshEdits()
{
    if (!m_client) {
        return;
    }
    const auto docId = m_state ? m_state->documentId() : QString();
    m_statusLabel->setText(tr("Loading edits..."));
    m_client->fetchEdits(docId, m_offset, m_limit, [this](bool ok, const QJsonArray& arr, const QString& err) {
        if (!ok) {
            m_statusLabel->setText(tr("Failed: %1").arg(err));
            return;
        }
        populateTable(arr);
        m_statusLabel->setText(tr("Showing %1 edits (offset %2)").arg(arr.size()).arg(m_offset));
        m_prevButton->setEnabled(m_offset > 0);
        m_nextButton->setEnabled(arr.size() >= m_limit);
    });
}

void EditsWindow::nextPage()
{
    m_offset += m_limit;
    refreshEdits();
}

void EditsWindow::prevPage()
{
    m_offset = qMax(0, m_offset - m_limit);
    refreshEdits();
}
