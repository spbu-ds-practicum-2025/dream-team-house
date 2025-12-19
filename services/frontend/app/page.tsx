'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

type GenerationMode = 'light' | 'pro'

const REDIRECT_DELAY_MS = 1200

interface ModeConfig {
  name: string
  description: string
  maxEditsPerAgent: number
  tokenBudget: number
  agentCount: number
}

type RolePreset = {
  key: string
  name: string
  prompt: string
}

const ROLE_PRESETS: RolePreset[] = [
  { key: 'researcher', name: 'Исследователь', prompt: 'Добавляй факты, цифры и контекст, расширяя разделы примерами и источниками.' },
  { key: 'narrator', name: 'Нарративный писатель', prompt: 'Делай текст связным, добавляй переходы и разворачивай мысли в законченные абзацы.' },
  { key: 'analyst', name: 'Аналитик', prompt: 'Укрепляй аргументацию выводами, сравнениями и структурой без воды и повторов.' },
  { key: 'strategist', name: 'Стратег', prompt: 'Предлагай прикладные шаги, планы и сценарии применения с детальными рекомендациями.' },
  { key: 'quality_guard', name: 'Редактор качества', prompt: 'Убирай явные повторы, добавляй уточнения и разъяснения, сохраняя стиль.' },
  { key: 'storyfinder', name: 'Охотник за примерами', prompt: 'Расширяй текст кейсами, мини-историями и жизненными примерами.' },
  { key: 'visionary', name: 'Визионер', prompt: 'Добавляй содержательные идеи о будущем, трендах и последствиях без лишнего пафоса.' },
  { key: 'connector', name: 'Связующий', prompt: 'Добавляй мостики между разделами, показывай связи и логику повествования.' },
  { key: 'localizer', name: 'Локализатор', prompt: 'Адаптируй контент под аудиторию, добавляй отраслевые и культурные нюансы.' },
  { key: 'mentor', name: 'Ментор', prompt: 'Давай развёрнутые объяснения и советы, добавляй пошаговые инструкции без пустых просьб.' },
]

const ROLE_MAP = Object.fromEntries(ROLE_PRESETS.map((role) => [role.key, role]))

const DEFAULT_ROLE_KEYS: Record<GenerationMode, string[]> = {
  light: ['researcher', 'narrator', 'analyst'],
  pro: ['researcher', 'narrator', 'analyst', 'strategist', 'quality_guard', 'storyfinder', 'visionary', 'connector', 'localizer', 'mentor'],
}

const MODES: Record<GenerationMode, ModeConfig> = {
  light: {
    name: 'Light',
    description: 'Быстрая генерация с упором на 3 содержательные правки у каждого агента',
    maxEditsPerAgent: 3,
    tokenBudget: 50000,
    agentCount: 3,
  },
  pro: {
    name: 'Pro',
    description: 'Полноценная генерация: каждый агент может сделать до 10 плотных итераций',
    maxEditsPerAgent: 10,
    tokenBudget: 500000,
    agentCount: 10,
  },
}

const ensureRoleList = (mode: GenerationMode, roles: RolePreset[]) => {
  const required = MODES[mode].agentCount
  if (roles.length >= required) return roles.slice(0, required)
  const defaults = DEFAULT_ROLE_KEYS[mode].map((key) => ROLE_MAP[key] || ROLE_PRESETS[0])
  const combined = [...roles]
  for (let i = roles.length; i < required; i++) {
    combined.push(defaults[i % defaults.length])
  }
  return combined
}

const defaultRolesForMode = (mode: GenerationMode) =>
  ensureRoleList(mode, DEFAULT_ROLE_KEYS[mode].map((key) => ROLE_MAP[key] || ROLE_PRESETS[0]))

export default function Home() {
  const router = useRouter()
  const [topic, setTopic] = useState('')
  const [initialText, setInitialText] = useState('')
  const [mode, setMode] = useState<GenerationMode>('light')
  const [agentRoles, setAgentRoles] = useState<RolePreset[]>(defaultRolesForMode('light'))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost'
  const normalizedRoles = ensureRoleList(mode, agentRoles)

  const handleModeChange = (modeKey: GenerationMode) => {
    setMode(modeKey)
    setAgentRoles(defaultRolesForMode(modeKey))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess(false)

    try {
      const normalizedRoles = ensureRoleList(mode, agentRoles)
      const rolesPayload = normalizedRoles.map((role) => ({
        role_key: role.key,
        name: role.name,
        prompt: role.prompt,
      }))
      const perAgentEdits = MODES[mode].maxEditsPerAgent
      const agentCount = MODES[mode].agentCount
      const totalEdits = perAgentEdits * agentCount

      const response = await fetch(`${API_URL}/api/document/init`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          topic,
          initial_text: initialText,
          mode,
          max_edits: totalEdits,
          max_edits_per_agent: perAgentEdits,
          agent_count: agentCount,
          agent_roles: rolesPayload,
          token_budget: MODES[mode].tokenBudget,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to initialize document')
      }

      const data = await response.json()
      setSuccess(true)
      setTimeout(() => {
        router.push(`/document?documentId=${encodeURIComponent(data.document_id)}`)
      }, REDIRECT_DELAY_MS)
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
              <h1 className="text-xl sm:text-2xl font-bold text-indigo-600">Dream Team House</h1>
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
            Выберите режим генерации в зависимости от ваших потребностей.
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
                Начальный текст (необязательно)
              </label>
              <textarea
                id="initialText"
                value={initialText}
                onChange={(e) => setInitialText(e.target.value)}
                rows={4}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="Введите начальный текст документа..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Режим генерации
              </label>
              <div className="flex flex-col lg:flex-row gap-4">
                {(Object.keys(MODES) as GenerationMode[]).map((modeKey) => {
                  const modeConfig = MODES[modeKey]
                  const isSelected = mode === modeKey
                  return (
                    <button
                      key={modeKey}
                      type="button"
                      onClick={() => handleModeChange(modeKey)}
                      className={`p-4 border-2 rounded-lg text-left transition-all w-full ${
                         isSelected
                           ? 'border-indigo-600 bg-indigo-50'
                           : 'border-gray-200 hover:border-indigo-300'
                       }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className={`font-semibold text-lg ${isSelected ? 'text-indigo-600' : 'text-gray-900'}`}>
                          {modeConfig.name}
                        </span>
                        {isSelected && (
                          <span className="text-indigo-600">✓</span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 mb-3">{modeConfig.description}</p>
                      <div className="text-xs text-gray-500 space-y-1">
                        <p>• {modeConfig.agentCount} агента</p>
                        <p>• До {modeConfig.maxEditsPerAgent} правок на каждого</p>
                        <p>• Всего: {modeConfig.maxEditsPerAgent * modeConfig.agentCount} правок</p>
                        <p>• Лимит: {(modeConfig.tokenBudget / 1000).toFixed(0)}K токенов</p>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>

            <div>
              <div className="flex items-start justify-between mb-2">
                <label className="block text-sm font-medium text-gray-700">
                  Роли агентов ({MODES[mode].agentCount})
                </label>
                <span className="text-xs text-gray-500">
                  Одна правка = один полный цикл агента
                </span>
              </div>
              <p className="text-sm text-gray-600 mb-3">
                Выберите, как будут работать агенты. Каждый агент может сделать до {MODES[mode].maxEditsPerAgent} правок в выбранной роли.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {Array.from({ length: MODES[mode].agentCount }).map((_, idx) => {
                  const selectedRole = normalizedRoles[idx] || ROLE_PRESETS[0]
                  return (
                    <div key={idx} className="p-4 border border-gray-200 rounded-lg bg-gray-50">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-semibold text-gray-800">Агент #{idx + 1}</span>
                        <span className="text-xs text-indigo-600">{selectedRole.name}</span>
                      </div>
                      <select
                        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm mb-2"
                        value={selectedRole.key}
                        onChange={(e) => {
                          const chosen = ROLE_MAP[e.target.value] || ROLE_PRESETS[0]
                          setAgentRoles((prev) => {
                            const next = ensureRoleList(mode, prev)
                            next[idx] = chosen
                            return [...next]
                          })
                        }}
                      >
                        {ROLE_PRESETS.map((role) => (
                          <option key={role.key} value={role.key}>
                            {role.name}
                          </option>
                        ))}
                      </select>
                      <p className="text-xs text-gray-600 leading-relaxed">
                        {selectedRole.prompt}
                      </p>
                    </div>
                  )
                })}
              </div>
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
              {loading ? 'Создание...' : `Создать документ (${MODES[mode].name})`}
            </button>
          </form>

          <div className="mt-8 p-4 bg-blue-50 rounded-md">
              <h3 className="font-semibold text-blue-900 mb-2">ℹ️ Как это работает:</h3>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>• Документ будет реплицирован на 3 узла (Москва, Санкт-Петербург, Новосибирск)</li>
                <li>• {MODES[mode].agentCount} AI-агентов с заданными ролями работают параллельно</li>
                <li>• Каждый агент делает до {MODES[mode].maxEditsPerAgent} завершённых правок (цикл = один запрос ко всем стадиям)</li>
                <li>• Итоговый лимит правок на документ: {MODES[mode].maxEditsPerAgent * MODES[mode].agentCount}</li>
                <li>• Все изменения видны в реальном времени, лимит токенов остаётся прежним</li>
              </ul>
            </div>
          </div>
        </main>
      </div>
  )
}
