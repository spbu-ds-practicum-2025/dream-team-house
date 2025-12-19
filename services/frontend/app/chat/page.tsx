'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'

interface ChatMessage {
  message_id: string
  document_id?: string | null
  agent_id: string
  agent_role?: string | null
  message: string
  timestamp: string
  intent?: Record<string, unknown> | null
  comment?: Record<string, unknown> | null
}

interface DocumentSummary {
  document_id: string
  topic: string
  status: string
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [documents, setDocuments] = useState<DocumentSummary[]>([])
  const [selectedDocumentId, setSelectedDocumentId] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(true)

  const CHAT_URL = process.env.NEXT_PUBLIC_CHAT_URL || 'http://localhost'
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost'

  const fetchMessages = useCallback(async () => {
    try {
      const params = new URLSearchParams({ limit: '100' })
      if (selectedDocumentId) {
        params.append('document_id', selectedDocumentId)
      }
      const response = await fetch(`${CHAT_URL}/api/chat/messages?${params.toString()}`)
      if (!response.ok) {
        throw new Error('Failed to fetch messages')
      }
      const data = await response.json()
      setMessages(data.reverse())
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }, [CHAT_URL, selectedDocumentId])

  const fetchDocuments = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/documents`)
      if (!response.ok) {
        throw new Error('Failed to fetch documents')
      }
      const data = await response.json()
      setDocuments(data)
    } catch (err) {
      console.error('Error fetching documents', err)
    }
  }, [API_URL])

  useEffect(() => {
    fetchDocuments()
    fetchMessages()

    if (autoRefresh) {
      const interval = setInterval(fetchMessages, 2000)
      return () => clearInterval(interval)
    }
  }, [autoRefresh, fetchDocuments, fetchMessages])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Загрузка чата...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link href="/" className="text-2xl font-bold text-indigo-600">
                Dream Team House
              </Link>
            </div>
            <div className="flex items-center space-x-4">
              <Link href="/document" className="text-gray-700 hover:text-indigo-600 px-3 py-2 rounded-md text-sm font-medium">
                Документ
              </Link>
              <Link href="/chat" className="text-indigo-600 px-3 py-2 rounded-md text-sm font-medium">
                Чат
              </Link>
              <Link href="/analytics" className="text-gray-700 hover:text-indigo-600 px-3 py-2 rounded-md text-sm font-medium">
                Аналитика
              </Link>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Чат агентов</h1>
          <div className="flex items-center space-x-4">
            <select
              className="px-3 py-2 border border-gray-300 rounded-md text-sm"
              value={selectedDocumentId}
              onChange={(e) => setSelectedDocumentId(e.target.value)}
            >
              <option value="">Все документы</option>
              {documents.map((doc) => (
                <option key={doc.document_id} value={doc.document_id}>
                  {doc.topic} ({doc.status})
                </option>
              ))}
            </select>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              <span className="text-sm text-gray-700">Авто-обновление</span>
            </label>
            <button
              onClick={fetchMessages}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm"
            >
              Обновить
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-800">❌ Ошибка: {error}</p>
          </div>
        )}

        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b border-gray-200">
            <p className="text-sm text-gray-600">
              💬 Всего сообщений: <strong>{messages.length}</strong>
            </p>
          </div>
          
          <div className="divide-y divide-gray-200 max-h-[70vh] overflow-y-auto">
            {messages.length > 0 ? (
              messages.map((msg) => (
                <div key={msg.message_id} className="p-4 hover:bg-gray-50 transition-colors">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <span className="inline-flex items-center justify-center h-8 w-8 rounded-full bg-indigo-100 text-indigo-600 font-medium text-sm">
                        {msg.agent_id.substring(6, 8).toUpperCase()}
                      </span>
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {msg.agent_id}
                        </p>
                        {msg.agent_role && (
                          <p className="text-xs text-indigo-700 bg-indigo-50 inline-block px-2 py-1 rounded mt-1">
                            {msg.agent_role}
                          </p>
                        )}
                        <p className="text-xs text-gray-500">
                          {new Date(msg.timestamp).toLocaleString('ru-RU')}
                        </p>
                      </div>
                    </div>
                    {msg.document_id && (
                      <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs font-medium">
                        {msg.document_id.slice(0, 8)}
                      </span>
                    )}
                    {msg.intent && (
                      <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs font-medium">
                        Intent
                      </span>
                    )}
                    {msg.comment && (
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium">
                        Comment
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-700 ml-10 whitespace-pre-wrap">
                    {msg.message}
                  </p>
                </div>
              ))
            ) : (
              <div className="p-12 text-center text-gray-500">
                <p>Пока нет сообщений</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
