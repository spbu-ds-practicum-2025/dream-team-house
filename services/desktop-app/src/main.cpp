#include <QApplication>

#include "api_client.h"
#include "app_config.h"
#include "main_window.h"
#include "session_state.h"
#include "window_manager.h"

int main(int argc, char* argv[])
{
    QApplication app(argc, argv);
    app.setApplicationName(QStringLiteral("Dream Team House Desktop"));
    app.setOrganizationName(QStringLiteral("Dream Team House"));

    const auto config = loadAppConfig(app);
    app.setApplicationVersion(config.version);

    auto* state = new SessionState(&app);
    auto* api = new ApiClient(config, &app);
    auto* manager = new WindowManager(api, state, &app);

    auto* mainWindow = new MainWindow(manager);
    manager->setMainWindow(mainWindow);
    mainWindow->show();

    // Start with init/document windows easily reachable
    manager->showOrActivate(WindowType::Init);

    return app.exec();
}
