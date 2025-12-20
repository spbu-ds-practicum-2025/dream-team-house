#include "init_document_window.h"

#include <QLabel>
#include <QLineEdit>
#include <QMessageBox>
#include <QPushButton>
#include <QStatusBar>
#include <QTextEdit>
#include <QVBoxLayout>
#include <QWidget>

#include "api_client.h"
#include "navigation_bar.h"
#include "session_state.h"
#include "window_manager.h"

InitDocumentWindow::InitDocumentWindow(WindowManager* manager, ApiClient* client, SessionState* state, QWidget* parent)
    : QMainWindow(parent)
    , m_manager(manager)
    , m_client(client)
    , m_state(state)
    , m_topicEdit(nullptr)
    , m_initialTextEdit(nullptr)
    , m_statusLabel(nullptr)
    , m_initButton(nullptr)
{
    setupUi();
}

void InitDocumentWindow::setupUi()
{
    setWindowTitle(tr("Init Document"));
    resize(520, 420);

    auto* central = new QWidget(this);
    auto* layout = new QVBoxLayout(central);
    layout->setContentsMargins(12, 12, 12, 12);
    layout->setSpacing(8);

    layout->addWidget(new NavigationBar(m_manager, this));

    m_statusLabel = new QLabel(tr("Provide topic and initial text."));
    layout->addWidget(m_statusLabel);

    m_topicEdit = new QLineEdit(this);
    m_topicEdit->setPlaceholderText(tr("Topic"));
    layout->addWidget(m_topicEdit);

    m_initialTextEdit = new QTextEdit(this);
    m_initialTextEdit->setPlaceholderText(tr("Initial text"));
    m_initialTextEdit->setMinimumHeight(200);
    layout->addWidget(m_initialTextEdit);

    m_initButton = new QPushButton(tr("Init"), this);
    layout->addWidget(m_initButton);

    connect(m_initButton, &QPushButton::clicked, this, &InitDocumentWindow::handleInit);

    setCentralWidget(central);
    statusBar()->showMessage(tr("Ready"));
}

void InitDocumentWindow::handleInit()
{
    if (!m_client) {
        QMessageBox::warning(this, tr("Error"), tr("API client is not available."));
        return;
    }
    const auto topic = m_topicEdit->text().trimmed();
    const auto initial = m_initialTextEdit->toPlainText().trimmed();
    if (topic.isEmpty()) {
        QMessageBox::warning(this, tr("Validation"), tr("Topic must not be empty."));
        return;
    }
    m_initButton->setEnabled(false);
    m_statusLabel->setText(tr("Sending request..."));

    m_client->initDocument(topic, initial, [this](bool ok, const QString& documentId, const QString& status) {
        m_initButton->setEnabled(true);
        if (!ok) {
            m_statusLabel->setText(tr("Failed to init document."));
            QMessageBox::critical(this, tr("Init failed"), status);
            return;
        }
        if (m_state) {
            m_state->setDocumentId(documentId);
        }
        m_statusLabel->setText(tr("Document initialized: %1").arg(documentId));
        QMessageBox::information(this, tr("Success"), tr("Document initialized.\nStatus: %1\nID: %2").arg(status, documentId));
    });
}
