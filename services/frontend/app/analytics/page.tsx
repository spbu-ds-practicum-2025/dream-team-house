'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { ResponsiveContainer, AreaChart, Area, CartesianGrid, XAxis, YAxis, Tooltip, BarChart, Bar } from 'recharts'

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
  const tokenSeries = metrics?.token_usage_by_time.map((point) => ({
    time: new Date(point.timestamp).toLocaleString('ru-RU', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }),
    value: point.value,
  })) ?? []
  const activitySpark = metrics ? [
    { name: 'Правки', value: metrics.total_edits },
    { name: 'Агенты', value: metrics.active_agents },
    { name: 'Правок/мин', value: Number(metrics.edits_per_minute.toFixed(2)) },
  ] : []
  const tokenChartData = tokenSeries.length ? tokenSeries : [{ time: '—', value: 0 }]
  const activityData = activitySpark.length ? activitySpark : [{ name: 'Нет данных', value: 0 }]

  const fetchMetrics = useCallback(async () => {
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
  }, [ANALYTICS_URL, period])
  useEffect(() => {
    fetchMetrics()
  }, [fetchMetrics])

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link href="/" className="text-xl sm:text-2xl font-bold text-indigo-600">
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
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={tokenChartData}>
                    <defs>
                      <linearGradient id="colorTokens" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.35}/>
                        <stop offset="95%" stopColor="#4f46e5" stopOpacity={0.05}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="time" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Area type="monotone" dataKey="value" stroke="#4f46e5" fill="url(#colorTokens)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6 mt-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Пульс активности
              </h2>
              <div className="h-60">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={activityData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#818cf8" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
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
