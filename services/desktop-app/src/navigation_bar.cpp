#include "navigation_bar.h"

#include <QHBoxLayout>
#include <QPushButton>

NavigationBar::NavigationBar(WindowManager* manager, QWidget* parent)
    : QWidget(parent)
    , m_manager(manager)
{
    auto* layout = new QHBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(8);

    addButton(tr("Home"), WindowType::Main);
    addButton(tr("Init"), WindowType::Init);
    addButton(tr("Document"), WindowType::Document);
    addButton(tr("Edits"), WindowType::Edits);
    addButton(tr("Chat"), WindowType::Chat);
    addButton(tr("Analytics"), WindowType::Analytics);
    addButton(tr("Settings"), WindowType::Settings);
    layout->addStretch();
}

void NavigationBar::addButton(const QString& text, WindowType type)
{
    auto* btn = new QPushButton(text, this);
    btn->setFixedHeight(28);
    connect(btn, &QPushButton::clicked, this, [this, type]() {
        if (m_manager) {
            m_manager->showOrActivate(type);
        }
    });
    layout()->addWidget(btn);
}
