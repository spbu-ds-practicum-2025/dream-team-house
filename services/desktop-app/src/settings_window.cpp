#include "settings_window.h"

#include <QApplication>
#include <QClipboard>
#include <QCheckBox>
#include <QColor>
#include <QLabel>
#include <QPalette>
#include <QPushButton>
#include <QStatusBar>
#include <QVBoxLayout>
#include <QWidget>

#include "api_client.h"
#include "navigation_bar.h"
#include "session_state.h"
#include "window_manager.h"

SettingsWindow::SettingsWindow(WindowManager* manager, ApiClient* client, SessionState* state, QWidget* parent)
    : QMainWindow(parent)
    , m_manager(manager)
    , m_client(client)
    , m_state(state)
    , m_infoLabel(nullptr)
    , m_copyButton(nullptr)
    , m_darkTheme(nullptr)
{
    setupUi();
}

void SettingsWindow::setupUi()
{
    setWindowTitle(tr("Settings / About"));
    resize(520, 360);

    auto* central = new QWidget(this);
    auto* layout = new QVBoxLayout(central);
    layout->setContentsMargins(12, 12, 12, 12);
    layout->setSpacing(8);

    layout->addWidget(new NavigationBar(m_manager, this));

    m_infoLabel = new QLabel(diagnosticsText(), this);
    m_infoLabel->setWordWrap(true);
    layout->addWidget(m_infoLabel);

    m_copyButton = new QPushButton(tr("Copy diagnostics"), this);
    connect(m_copyButton, &QPushButton::clicked, this, &SettingsWindow::copyDiagnostics);
    layout->addWidget(m_copyButton);

    m_darkTheme = new QCheckBox(tr("Enable dark theme"), this);
    connect(m_darkTheme, &QCheckBox::toggled, this, &SettingsWindow::toggleDarkTheme);
    layout->addWidget(m_darkTheme);

    layout->addStretch();

    setCentralWidget(central);
    statusBar()->showMessage(tr("Diagnostics and theme"));
}

QString SettingsWindow::diagnosticsText() const
{
    const auto api = m_manager ? m_manager->api() : nullptr;
    QString text;
    text += tr("App version: %1\n").arg(qApp->applicationVersion());
    if (api) {
        text += tr("Text API: %1\nChat API: %2\nAnalytics API: %3\n")
                    .arg(api->textApiBase().toString(), api->chatApiBase().toString(), api->analyticsApiBase().toString());
    }
    text += tr("Document ID: %1\n").arg(m_state && !m_state->documentId().isEmpty() ? m_state->documentId() : tr("not set"));
    return text;
}

void SettingsWindow::copyDiagnostics()
{
    QApplication::clipboard()->setText(diagnosticsText());
    statusBar()->showMessage(tr("Diagnostics copied"), 2000);
}

void SettingsWindow::toggleDarkTheme(bool enabled)
{
    QPalette pal;
    if (enabled) {
        pal = QPalette();
        pal.setColor(QPalette::Window, QColor(53, 53, 53));
        pal.setColor(QPalette::WindowText, Qt::white);
        pal.setColor(QPalette::Base, QColor(25, 25, 25));
        pal.setColor(QPalette::AlternateBase, QColor(53, 53, 53));
        pal.setColor(QPalette::ToolTipBase, Qt::white);
        pal.setColor(QPalette::ToolTipText, Qt::white);
        pal.setColor(QPalette::Text, Qt::white);
        pal.setColor(QPalette::Button, QColor(53, 53, 53));
        pal.setColor(QPalette::ButtonText, Qt::white);
        pal.setColor(QPalette::BrightText, Qt::red);
    }
    QApplication::setPalette(pal);
}
