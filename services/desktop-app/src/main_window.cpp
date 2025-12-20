#include "main_window.h"

#include <QApplication>
#include <QGridLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QStatusBar>
#include <QVBoxLayout>
#include <QWidget>

#include "api_client.h"
#include "navigation_bar.h"
#include "session_state.h"

MainWindow::MainWindow(WindowManager* manager, QWidget* parent)
    : QMainWindow(parent)
    , m_manager(manager)
    , m_state(manager ? manager->state() : nullptr)
    , m_documentIdLabel(nullptr)
    , m_versionLabel(nullptr)
    , m_urlsLabel(nullptr)
{
    setupUi();
    refreshState();

    if (m_state) {
        connect(m_state, &SessionState::documentChanged, this, &MainWindow::refreshState);
    }
}

void MainWindow::setupUi()
{
    setWindowTitle(tr("Dream Team House — Desktop"));
    resize(640, 320);

    auto* central = new QWidget(this);
    auto* layout = new QVBoxLayout(central);
    layout->setContentsMargins(12, 12, 12, 12);
    layout->setSpacing(12);

    layout->addWidget(new NavigationBar(m_manager, this));

    auto* grid = new QGridLayout();
    grid->setHorizontalSpacing(16);
    grid->setVerticalSpacing(10);

    int row = 0;
    grid->addWidget(new QLabel(tr("Current Document ID:")), row, 0);
    m_documentIdLabel = new QLabel(tr("—"));
    grid->addWidget(m_documentIdLabel, row, 1);
    row++;

    grid->addWidget(new QLabel(tr("Version / Status:")), row, 0);
    m_versionLabel = new QLabel(tr("—"));
    grid->addWidget(m_versionLabel, row, 1);
    row++;

    grid->addWidget(new QLabel(tr("Service URLs:")), row, 0);
    m_urlsLabel = new QLabel(tr("—"));
    m_urlsLabel->setWordWrap(true);
    grid->addWidget(m_urlsLabel, row, 1);
    row++;

    layout->addLayout(grid);

    auto* buttonsLayout = new QHBoxLayout();
    buttonsLayout->setSpacing(10);

    auto addNavButton = [this, buttonsLayout](const QString& text, WindowType type) {
        auto* btn = new QPushButton(text, this);
        btn->setMinimumWidth(120);
        connect(btn, &QPushButton::clicked, this, [this, type]() {
            if (m_manager) {
                m_manager->showOrActivate(type);
            }
        });
        buttonsLayout->addWidget(btn);
    };

    addNavButton(tr("Init Document"), WindowType::Init);
    addNavButton(tr("Open Document"), WindowType::Document);
    addNavButton(tr("View Edits"), WindowType::Edits);
    addNavButton(tr("Chat"), WindowType::Chat);
    addNavButton(tr("Analytics"), WindowType::Analytics);
    addNavButton(tr("Settings"), WindowType::Settings);
    buttonsLayout->addStretch();
    layout->addLayout(buttonsLayout);

    setCentralWidget(central);
    statusBar()->showMessage(tr("Ready"));
}

void MainWindow::refreshState()
{
    if (!m_state) {
        return;
    }
    const QString docId = m_state->documentId().isEmpty() ? tr("not initialized") : m_state->documentId();
    m_documentIdLabel->setText(docId);

    const auto api = m_manager ? m_manager->api() : nullptr;
    QString urlsText;
    if (api) {
        urlsText = tr("Text API: %1\nChat API: %2\nAnalytics API: %3")
                       .arg(api->textApiBase().toString(), api->chatApiBase().toString(), api->analyticsApiBase().toString());
    }
    m_urlsLabel->setText(urlsText.isEmpty() ? tr("—") : urlsText);
    m_versionLabel->setText(qApp->applicationVersion());
}
