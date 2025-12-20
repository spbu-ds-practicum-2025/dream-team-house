#pragma once

#include <QWidget>

#include "window_manager.h"

class NavigationBar : public QWidget {
    Q_OBJECT
public:
    explicit NavigationBar(WindowManager* manager, QWidget* parent = nullptr);

private:
    void addButton(const QString& text, WindowType type);

    WindowManager* m_manager;
};
