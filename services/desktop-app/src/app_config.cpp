#include "app_config.h"

#include <QCommandLineOption>
#include <QCommandLineParser>
#include <QCoreApplication>
#include <QProcessEnvironment>
#include <QString>
#include <QtGlobal>

#include "generated_config.h"

static QString envOrDefault(const char* key, const QString& fallback)
{
    const auto env = qEnvironmentVariable(key);
    if (!env.isEmpty()) {
        return env;
    }
    return fallback;
}

AppConfig loadAppConfig(const QCoreApplication& app)
{
    AppConfig config;
    config.textApiUrl = envOrDefault("DTH_API_URL", QStringLiteral(DTH_DEFAULT_TEXT_API_URL));
    config.chatApiUrl = envOrDefault("DTH_CHAT_URL", QStringLiteral(DTH_DEFAULT_CHAT_API_URL));
    config.analyticsApiUrl = envOrDefault("DTH_ANALYTICS_URL", QStringLiteral(DTH_DEFAULT_ANALYTICS_API_URL));
    config.version = QStringLiteral(DTH_APP_VERSION);

    QCommandLineParser parser;
    parser.setApplicationDescription(QStringLiteral("Dream Team House Desktop"));
    parser.addHelpOption();
    parser.addVersionOption();

    QCommandLineOption apiUrlOpt(QStringList() << "u"
                                               << "api-url",
                                 QStringLiteral("Override Text API base URL"),
                                 QStringLiteral("url"));
    QCommandLineOption chatUrlOpt(QStringList() << "c"
                                                << "chat-url",
                                  QStringLiteral("Override Chat API base URL"),
                                  QStringLiteral("url"));
    QCommandLineOption analyticsUrlOpt(QStringList() << "a"
                                                     << "analytics-url",
                                       QStringLiteral("Override Analytics API base URL"),
                                       QStringLiteral("url"));

    parser.addOption(apiUrlOpt);
    parser.addOption(chatUrlOpt);
    parser.addOption(analyticsUrlOpt);

    parser.process(app);

    if (parser.isSet(apiUrlOpt)) {
        config.textApiUrl = parser.value(apiUrlOpt);
    }
    if (parser.isSet(chatUrlOpt)) {
        config.chatApiUrl = parser.value(chatUrlOpt);
    }
    if (parser.isSet(analyticsUrlOpt)) {
        config.analyticsApiUrl = parser.value(analyticsUrlOpt);
    }

    return config;
}
