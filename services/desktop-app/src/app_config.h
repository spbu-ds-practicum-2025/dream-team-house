#pragma once

#include <QCoreApplication>
#include <QString>

struct AppConfig {
    QString textApiUrl;
    QString chatApiUrl;
    QString analyticsApiUrl;
    QString version;
};

/**
 * @brief Load application configuration from compile-time defaults with optional overrides.
 *
 * Order of precedence:
 *  1. Command line options (--api-url, --chat-url, --analytics-url)
 *  2. Environment variables (DTH_API_URL, DTH_CHAT_URL, DTH_ANALYTICS_URL)
 *  3. Compile-time defaults baked into the build
 */
AppConfig loadAppConfig(const QCoreApplication& app);
