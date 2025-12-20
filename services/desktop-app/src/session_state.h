#pragma once

#include <QObject>
#include <QString>

class SessionState : public QObject {
    Q_OBJECT
public:
    explicit SessionState(QObject* parent = nullptr) : QObject(parent) {}

    QString documentId() const { return m_documentId; }
    void setDocumentId(const QString& id)
    {
        if (id != m_documentId) {
            m_documentId = id;
            emit documentChanged(id);
        }
    }

    QString lastChatSince() const { return m_lastChatSince; }
    void setLastChatSince(const QString& since) { m_lastChatSince = since; }

signals:
    void documentChanged(const QString& newId);

private:
    QString m_documentId;
    QString m_lastChatSince;
};
