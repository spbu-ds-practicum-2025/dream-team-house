#include "chat_window.h"

#include <QAbstractItemView>
#include <QJsonArray>
#include <QJsonObject>
#include <QHBoxLayout>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QListWidgetItem>
#include <QPushButton>
#include <QStatusBar>
#include <QVBoxLayout>
#include <QWidget>

#include "api_client.h"
#include "navigation_bar.h"
#include "session_state.h"
#include "window_manager.h"

ChatWindow::ChatWindow(WindowManager* manager, ApiClient* client, SessionState* state, QWidget* parent)
    : QMainWindow(parent)
    , m_manager(manager)
    , m_client(client)
    , m_state(state)
    , m_list(nullptr)
    , m_statusLabel(nullptr)
    , m_filterEdit(nullptr)
    , m_refreshButton(nullptr)
{
    setupUi();
    startTimer();
}

ChatWindow::~ChatWindow()
{
    m_timer.stop();
}

void ChatWindow::setupUi()
{
    setWindowTitle(tr("Chat"));
    resize(640, 500);

    auto* central = new QWidget(this);
    auto* layout = new QVBoxLayout(central);
    layout->setContentsMargins(12, 12, 12, 12);
    layout->setSpacing(8);

    layout->addWidget(new NavigationBar(m_manager, this));

    auto* filterLayout = new QHBoxLayout();
    filterLayout->addWidget(new QLabel(tr("Document filter:"), this));
    m_filterEdit = new QLineEdit(this);
    filterLayout->addWidget(m_filterEdit, 1);
    m_refreshButton = new QPushButton(tr("Refresh"), this);
    filterLayout->addWidget(m_refreshButton);
    layout->addLayout(filterLayout);

    m_list = new QListWidget(this);
    m_list->setSelectionMode(QAbstractItemView::NoSelection);
    layout->addWidget(m_list, 1);

    m_statusLabel = new QLabel(this);
    layout->addWidget(m_statusLabel);

    connect(m_refreshButton, &QPushButton::clicked, this, &ChatWindow::applyFilter);
    connect(m_filterEdit, &QLineEdit::editingFinished, this, &ChatWindow::applyFilter);

    setCentralWidget(central);
    statusBar()->showMessage(tr("Auto-refresh every 3s"));
}

void ChatWindow::startTimer()
{
    m_timer.setInterval(3000);
    connect(&m_timer, &QTimer::timeout, this, &ChatWindow::refreshChat);
    m_timer.start();
}

void ChatWindow::appendMessages(const QJsonArray& arr)
{
    for (const auto& value : arr) {
        const auto obj = value.toObject();
        const auto docId = obj.value("document_id").toString();
        if (!m_filterEdit->text().isEmpty() && docId != m_filterEdit->text()) {
            continue;
        }
        const QString text = QString("[%1] %2: %3")
                                 .arg(obj.value("timestamp").toString(),
                                      obj.value("agent_id").toString(),
                                      obj.value("message").toString());
        auto* item = new QListWidgetItem(text);
        item->setToolTip(docId.isEmpty() ? tr("No document filter") : tr("Document: %1").arg(docId));
        m_list->addItem(item);
    }
    m_list->scrollToBottom();
}

void ChatWindow::refreshChat()
{
    if (!m_client) {
        return;
    }
    const QString docId = m_filterEdit->text().isEmpty() && m_state ? m_state->documentId() : m_filterEdit->text();
    const QString since = m_state ? m_state->lastChatSince() : QString();
    m_client->fetchChatMessages(docId, since, 100, [this](bool ok, const QJsonArray& arr, const QString& err) {
        if (!ok) {
            m_statusLabel->setText(tr("Failed: %1").arg(err));
            return;
        }
        appendMessages(arr);
        if (!arr.isEmpty() && m_state) {
            const auto last = arr.last().toObject();
            m_state->setLastChatSince(last.value("timestamp").toString());
        }
        m_statusLabel->setText(tr("Messages: %1").arg(m_list->count()));
    });
}

void ChatWindow::applyFilter()
{
    m_list->clear();
    if (m_state) {
        m_state->setLastChatSince(QString());
    }
    refreshChat();
}
