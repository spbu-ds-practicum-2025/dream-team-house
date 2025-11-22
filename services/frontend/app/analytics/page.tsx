'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'

interface Metrics {
  total_edits: number
  total_tokens: number
  active_agents: number
  avg_latency_ms: number
  edits_per_minute: number
  token_usage_by_time: Array<{ timestamp: string; value: number }>
}

export default function AnalyticsPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [period, setPeriod] = useState('1h')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const ANALYTICS_URL = process.env.NEXT_PUBLIC_ANALYTICS_URL || 'http://localhost'

  const fetchMetrics = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${ANALYTICS_URL}/api/analytics/metrics?period=${period}`)
      if (!response.ok) {
        throw new Error('Failed to fetch metrics')
      }
      const data = await response.json()
      setMetrics(data)
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMetrics()
  }, [period])

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
              <Link href="/chat" className="text-gray-700 hover:text-indigo-600 px-3 py-2 rounded-md text-sm font-medium">
                Чат
              </Link>
              <Link href="/analytics" className="text-indigo-600 px-3 py-2 rounded-md text-sm font-medium">
                Аналитика
              </Link>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Аналитика</h1>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setPeriod('1h')}
              className={`px-4 py-2 rounded-md text-sm font-medium ${
                period === '1h'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              1 час
            </button>
            <button
              onClick={() => setPeriod('24h')}
              className={`px-4 py-2 rounded-md text-sm font-medium ${
                period === '24h'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              24 часа
            </button>
            <button
              onClick={() => setPeriod('7d')}
              className={`px-4 py-2 rounded-md text-sm font-medium ${
                period === '7d'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              7 дней
            </button>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Загрузка метрик...</p>
          </div>
        ) : error ? (
          <div className="p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-800">❌ Ошибка: {error}</p>
          </div>
        ) : metrics ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Всего правок</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">
                      {metrics.total_edits}
                    </p>
                  </div>
                  <div className="h-12 w-12 bg-indigo-100 rounded-full flex items-center justify-center">
                    <span className="text-2xl">📝</span>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Токенов использовано</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">
                      {metrics.total_tokens.toLocaleString()}
                    </p>
                  </div>
                  <div className="h-12 w-12 bg-green-100 rounded-full flex items-center justify-center">
                    <span className="text-2xl">💰</span>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Активных агентов</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">
                      {metrics.active_agents}
                    </p>
                  </div>
                  <div className="h-12 w-12 bg-purple-100 rounded-full flex items-center justify-center">
                    <span className="text-2xl">🤖</span>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Правок/мин</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">
                      {metrics.edits_per_minute.toFixed(2)}
                    </p>
                  </div>
                  <div className="h-12 w-12 bg-yellow-100 rounded-full flex items-center justify-center">
                    <span className="text-2xl">⚡</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Использование токенов
              </h2>
              <div className="space-y-2">
                {metrics.token_usage_by_time.map((point, index) => (
                  <div key={index} className="flex items-center">
                    <div className="w-48 text-sm text-gray-600">
                      {new Date(point.timestamp).toLocaleString('ru-RU', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </div>
                    <div className="flex-1 ml-4">
                      <div className="bg-gray-200 rounded-full h-4">
                        <div
                          className="bg-indigo-600 h-4 rounded-full"
                          style={{
                            width: `${Math.min(
                              (point.value / Math.max(...metrics.token_usage_by_time.map((p) => p.value), 1)) * 100,
                              100
                            )}%`,
                          }}
                        ></div>
                      </div>
                    </div>
                    <div className="w-20 text-right text-sm font-medium text-gray-900">
                      {point.value}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {metrics.avg_latency_ms > 0 && (
              <div className="mt-6 bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-2">
                  Средняя задержка репликации
                </h2>
                <p className="text-3xl font-bold text-indigo-600">
                  {metrics.avg_latency_ms.toFixed(2)} мс
                </p>
              </div>
            )}
          </>
        ) : null}
      </main>
    </div>
  )
}
