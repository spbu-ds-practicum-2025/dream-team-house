#include "document_window.h"

#include <QDateTime>
#include <QJsonObject>
#include <QLabel>
#include <QPushButton>
#include <QStatusBar>
#include <QTextBrowser>
#include <QVBoxLayout>
#include <QWidget>

#include "api_client.h"
#include "navigation_bar.h"
#include "session_state.h"
#include "window_manager.h"

namespace {
constexpr int kRefreshIntervalMs = 2000;
}

DocumentWindow::DocumentWindow(WindowManager* manager, ApiClient* client, SessionState* state, QWidget* parent)
    : QMainWindow(parent)
    , m_manager(manager)
    , m_client(client)
    , m_state(state)
    , m_textView(nullptr)
    , m_metaLabel(nullptr)
    , m_errorLabel(nullptr)
    , m_refreshButton(nullptr)
{
    setupUi();
    startTimer();
}

DocumentWindow::~DocumentWindow()
{
    m_timer.stop();
}

void DocumentWindow::setupUi()
{
    setWindowTitle(tr("Document"));
    resize(640, 520);

    auto* central = new QWidget(this);
    auto* layout = new QVBoxLayout(central);
    layout->setContentsMargins(12, 12, 12, 12);
    layout->setSpacing(8);

    layout->addWidget(new NavigationBar(m_manager, this));

    m_metaLabel = new QLabel(tr("Waiting for document..."));
    layout->addWidget(m_metaLabel);

    m_textView = new QTextBrowser(this);
    m_textView->setReadOnly(true);
    layout->addWidget(m_textView, 1);

    m_errorLabel = new QLabel(this);
    m_errorLabel->setStyleSheet("color: red;");
    layout->addWidget(m_errorLabel);

    m_refreshButton = new QPushButton(tr("Refresh now"), this);
    connect(m_refreshButton, &QPushButton::clicked, this, &DocumentWindow::refreshDocument);
    layout->addWidget(m_refreshButton);

    setCentralWidget(central);
    statusBar()->showMessage(tr("Auto-refresh every 2s"));
}

void DocumentWindow::startTimer()
{
    m_timer.setInterval(kRefreshIntervalMs);
    connect(&m_timer, &QTimer::timeout, this, &DocumentWindow::refreshDocument);
    m_timer.start();
}

void DocumentWindow::refreshDocument()
{
    if (!m_client) {
        return;
    }
    const QString docId = m_state ? m_state->documentId() : QString();
    m_errorLabel->clear();
    m_client->fetchDocument(docId, [this](bool ok, const QJsonObject& obj, const QString& err) {
        if (!ok) {
            m_errorLabel->setText(err);
            return;
        }
        const auto text = obj.value("text").toString();
        const auto version = obj.value("version").toInt();
        const auto timestamp = obj.value("timestamp").toString();
        const auto topic = obj.value("topic").toString();
        const auto docId = obj.value("document_id").toString();
        if (m_state) {
            m_state->setDocumentId(docId);
        }
        m_textView->setPlainText(text);
        m_metaLabel->setText(tr("Topic: %1 | Version: %2 | %3")
                                 .arg(topic.isEmpty() ? tr("n/a") : topic)
                                 .arg(version)
                                 .arg(timestamp));
    });
}
