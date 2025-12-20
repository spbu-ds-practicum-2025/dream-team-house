#include "api_client.h"

#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QUrl>
#include <QUrlQuery>
#include <QtGlobal>

ApiClient::ApiClient(const AppConfig& config, QObject* parent)
    : QObject(parent)
    , m_config(config)
    , m_textApiBase(QUrl(config.textApiUrl))
    , m_chatApiBase(QUrl(config.chatApiUrl))
    , m_analyticsApiBase(QUrl(config.analyticsApiUrl))
    , m_manager(new QNetworkAccessManager(this))
{
}

QUrl ApiClient::makeUrl(const QUrl& base, const QString& path, const QUrlQuery& query) const
{
    QUrl url(base);
    url.setPath(path);
    if (!query.isEmpty()) {
        url.setQuery(query);
    }
    return url;
}

void ApiClient::performGet(const QUrl& url,
                           std::function<void(bool, const QJsonDocument&, const QString&)> callback)
{
    QNetworkRequest request(url);
    auto* reply = m_manager->get(request);
    connect(reply, &QNetworkReply::finished, this, [reply, callback]() {
        const auto statusCode = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const auto data = reply->readAll();
        QJsonParseError parseError;
        QJsonDocument doc = QJsonDocument::fromJson(data, &parseError);

        if (reply->error() != QNetworkReply::NoError) {
            callback(false, doc, reply->errorString());
        } else if (statusCode >= 400) {
            callback(false, doc, QStringLiteral("HTTP %1").arg(statusCode));
        } else if (parseError.error != QJsonParseError::NoError && !data.isEmpty()) {
            callback(false, doc, QStringLiteral("Parse error: %1").arg(parseError.errorString()));
        } else {
            callback(true, doc, QString());
        }
        reply->deleteLater();
    });
}

void ApiClient::performPost(const QUrl& url,
                            const QJsonObject& payload,
                            std::function<void(bool, const QJsonDocument&, const QString&)> callback)
{
    QNetworkRequest request(url);
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    const QByteArray body = QJsonDocument(payload).toJson();
    auto* reply = m_manager->post(request, body);
    connect(reply, &QNetworkReply::finished, this, [reply, callback]() {
        const auto statusCode = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const auto data = reply->readAll();
        QJsonParseError parseError;
        QJsonDocument doc = QJsonDocument::fromJson(data, &parseError);

        if (reply->error() != QNetworkReply::NoError) {
            callback(false, doc, reply->errorString());
        } else if (statusCode >= 400) {
            callback(false, doc, QStringLiteral("HTTP %1").arg(statusCode));
        } else if (parseError.error != QJsonParseError::NoError && !data.isEmpty()) {
            callback(false, doc, QStringLiteral("Parse error: %1").arg(parseError.errorString()));
        } else {
            callback(true, doc, QString());
        }
        reply->deleteLater();
    });
}

void ApiClient::initDocument(const QString& topic,
                             const QString& initialText,
                             std::function<void(bool, const QString&, const QString&)> callback)
{
    QJsonObject payload{
        {"topic", topic},
        {"initial_text", initialText},
    };
    const auto url = makeUrl(m_textApiBase, "/api/document/init");
    performPost(url, payload, [callback](bool ok, const QJsonDocument& doc, const QString& err) {
        if (!ok) {
            callback(false, QString(), err);
            return;
        }
        const auto obj = doc.object();
        callback(true, obj.value("document_id").toString(), obj.value("status").toString());
    });
}

void ApiClient::fetchDocument(const QString& documentId,
                              std::function<void(bool, const QJsonObject&, const QString&)> callback)
{
    QUrlQuery query;
    if (!documentId.isEmpty()) {
        query.addQueryItem("document_id", documentId);
    }
    const auto url = makeUrl(m_textApiBase, "/api/document/current", query);
    performGet(url, [callback](bool ok, const QJsonDocument& doc, const QString& err) {
        callback(ok, doc.object(), err);
    });
}

void ApiClient::fetchEdits(const QString& documentId,
                           int offset,
                           int limit,
                           std::function<void(bool, const QJsonArray&, const QString&)> callback)
{
    QUrlQuery query;
    query.addQueryItem("offset", QString::number(qMax(0, offset)));
    query.addQueryItem("limit", QString::number(qMax(1, limit)));
    if (!documentId.isEmpty()) {
        query.addQueryItem("document_id", documentId);
    }
    const auto url = makeUrl(m_textApiBase, "/api/edits", query);
    performGet(url, [callback](bool ok, const QJsonDocument& doc, const QString& err) {
        callback(ok, doc.array(), err);
    });
}

void ApiClient::fetchChatMessages(const QString& documentId,
                                  const QString& since,
                                  int limit,
                                  std::function<void(bool, const QJsonArray&, const QString&)> callback)
{
    QUrlQuery query;
    query.addQueryItem("limit", QString::number(qMax(1, limit)));
    if (!documentId.isEmpty()) {
        query.addQueryItem("document_id", documentId);
    }
    if (!since.isEmpty()) {
        query.addQueryItem("since", since);
    }
    const auto url = makeUrl(m_chatApiBase, "/api/chat/messages", query);
    performGet(url, [callback](bool ok, const QJsonDocument& doc, const QString& err) {
        callback(ok, doc.array(), err);
    });
}

void ApiClient::fetchAnalytics(const QString& period,
                               std::function<void(bool, const QJsonObject&, const QString&)> callback)
{
    QUrlQuery query;
    query.addQueryItem("period", period);
    const auto url = makeUrl(m_analyticsApiBase, "/api/analytics/metrics", query);
    performGet(url, [callback](bool ok, const QJsonDocument& doc, const QString& err) {
        callback(ok, doc.object(), err);
    });
}
