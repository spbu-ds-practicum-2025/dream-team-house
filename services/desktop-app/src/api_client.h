#pragma once

#include <functional>

#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QObject>
#include <QUrl>
#include <QUrlQuery>

#include "app_config.h"

class QNetworkAccessManager;
class QNetworkReply;

class ApiClient : public QObject {
    Q_OBJECT
public:
    explicit ApiClient(const AppConfig& config, QObject* parent = nullptr);

    const QUrl& textApiBase() const { return m_textApiBase; }
    const QUrl& chatApiBase() const { return m_chatApiBase; }
    const QUrl& analyticsApiBase() const { return m_analyticsApiBase; }

    void initDocument(const QString& topic,
                      const QString& initialText,
                      std::function<void(bool, const QString&, const QString&)> callback);

    void fetchDocument(const QString& documentId,
                       std::function<void(bool, const QJsonObject&, const QString&)> callback);

    void fetchEdits(const QString& documentId,
                    int offset,
                    int limit,
                    std::function<void(bool, const QJsonArray&, const QString&)> callback);

    void fetchChatMessages(const QString& documentId,
                           const QString& since,
                           int limit,
                           std::function<void(bool, const QJsonArray&, const QString&)> callback);

    void fetchAnalytics(const QString& period,
                        std::function<void(bool, const QJsonObject&, const QString&)> callback);

private:
    void performGet(const QUrl& url,
                    std::function<void(bool, const QJsonDocument&, const QString&)> callback);
    void performPost(const QUrl& url,
                     const QJsonObject& payload,
                     std::function<void(bool, const QJsonDocument&, const QString&)> callback);

    QUrl makeUrl(const QUrl& base, const QString& path, const QUrlQuery& query = {}) const;

    AppConfig m_config;
    QUrl m_textApiBase;
    QUrl m_chatApiBase;
    QUrl m_analyticsApiBase;
    QNetworkAccessManager* m_manager;
};
