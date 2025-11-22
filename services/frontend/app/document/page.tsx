'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'

interface Document {
  version: number
  text: string
  timestamp: string
}

interface Edit {
  edit_id: string
  agent_id: string
  operation: string
  status: string
  tokens_used: number
  created_at: string
}

export default function DocumentPage() {
  const [document, setDocument] = useState<Document | null>(null)
  const [edits, setEdits] = useState<Edit[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(true)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost'

  const fetchDocument = async () => {
    try {
      const response = await fetch(`${API_URL}/api/document/current`)
      if (!response.ok) {
        throw new Error('Failed to fetch document')
      }
      const data = await response.json()
      setDocument(data)
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const fetchEdits = async () => {
    try {
      const response = await fetch(`${API_URL}/api/edits?limit=20`)
      if (!response.ok) {
        throw new Error('Failed to fetch edits')
      }
      const data = await response.json()
      setEdits(data)
    } catch (err) {
      console.error('Error fetching edits:', err)
    }
  }

  useEffect(() => {
    fetchDocument()
    fetchEdits()

    if (autoRefresh) {
      const interval = setInterval(() => {
        fetchDocument()
        fetchEdits()
      }, 3000)
      return () => clearInterval(interval)
    }
  }, [autoRefresh])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Загрузка документа...</p>
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
              <Link href="/document" className="text-indigo-600 px-3 py-2 rounded-md text-sm font-medium">
                Документ
              </Link>
              <Link href="/chat" className="text-gray-700 hover:text-indigo-600 px-3 py-2 rounded-md text-sm font-medium">
                Чат
              </Link>
              <Link href="/analytics" className="text-gray-700 hover:text-indigo-600 px-3 py-2 rounded-md text-sm font-medium">
                Аналитика
              </Link>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Документ</h1>
          <div className="flex items-center space-x-4">
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
              onClick={() => {
                fetchDocument()
                fetchEdits()
              }}
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

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Document */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow p-6">
              {document ? (
                <>
                  <div className="flex justify-between items-center mb-4">
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900">
                        Версия: {document.version}
                      </h2>
                      <p className="text-sm text-gray-500">
                        {new Date(document.timestamp).toLocaleString('ru-RU')}
                      </p>
                    </div>
                    <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                      Активен
                    </span>
                  </div>
                  <div className="prose max-w-none">
                    <pre className="whitespace-pre-wrap text-gray-800 font-sans leading-relaxed">
                      {document.text}
                    </pre>
                  </div>
                </>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <p className="mb-4">Документ не найден</p>
                  <Link
                    href="/"
                    className="text-indigo-600 hover:text-indigo-700 underline"
                  >
                    Создать новый документ
                  </Link>
                </div>
              )}
            </div>
          </div>

          {/* Edits History */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                История правок
              </h2>
              <div className="space-y-3">
                {edits.length > 0 ? (
                  edits.map((edit) => (
                    <div
                      key={edit.edit_id}
                      className="p-3 bg-gray-50 rounded-md border border-gray-200"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-gray-600">
                          {edit.agent_id.substring(0, 12)}...
                        </span>
                        <span
                          className={`px-2 py-1 rounded text-xs font-medium ${
                            edit.status === 'accepted'
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {edit.status}
                        </span>
                      </div>
                      <p className="text-sm text-gray-700">
                        <strong>{edit.operation}</strong>
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        Токенов: {edit.tokens_used}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-gray-500 text-center py-4">
                    Пока нет правок
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
