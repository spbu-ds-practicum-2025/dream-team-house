'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

export default function Home() {
  const router = useRouter()
  const [topic, setTopic] = useState('')
  const [initialText, setInitialText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess(false)

    try {
      const response = await fetch(`${API_URL}/api/document/init`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          topic,
          initial_text: initialText,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to initialize document')
      }

      setSuccess(true)
      setTimeout(() => {
        router.push('/document')
      }, 1500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-indigo-600">Dream Team House</h1>
            </div>
            <div className="flex items-center space-x-4">
              <Link href="/document" className="text-gray-700 hover:text-indigo-600 px-3 py-2 rounded-md text-sm font-medium">
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

      <main className="max-w-4xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
        <div className="bg-white rounded-lg shadow-xl p-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">
            Создать новый документ
          </h2>
          
          <p className="text-gray-600 mb-8">
            Инициализируйте документ, и AI-агенты начнут коллективную работу над ним.
            Система использует 3 агента, каждый сделает до 2 правок.
          </p>

          {success && (
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-md">
              <p className="text-green-800">✅ Документ успешно создан! Перенаправление...</p>
            </div>
          )}

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-800">❌ Ошибка: {error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="topic" className="block text-sm font-medium text-gray-700 mb-2">
                Тема документа
              </label>
              <input
                type="text"
                id="topic"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                required
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="Например: История искусственного интеллекта"
              />
            </div>

            <div>
              <label htmlFor="initialText" className="block text-sm font-medium text-gray-700 mb-2">
                Начальный текст
              </label>
              <textarea
                id="initialText"
                value={initialText}
                onChange={(e) => setInitialText(e.target.value)}
                required
                rows={8}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="Введите начальный текст документа..."
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className={`w-full py-3 px-4 rounded-md text-white font-medium transition-colors ${
                loading
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-indigo-600 hover:bg-indigo-700'
              }`}
            >
              {loading ? 'Создание...' : 'Создать документ'}
            </button>
          </form>

          <div className="mt-8 p-4 bg-blue-50 rounded-md">
            <h3 className="font-semibold text-blue-900 mb-2">ℹ️ Как это работает:</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• Документ будет реплицирован на 3 узла (Москва, Санкт-Петербург, Новосибирск)</li>
              <li>• 3 AI-агента начнут работу одновременно</li>
              <li>• Каждый агент сделает до 2 правок</li>
              <li>• Все изменения будут видны в реальном времени</li>
            </ul>
          </div>
        </div>
      </main>
    </div>
  )
}
