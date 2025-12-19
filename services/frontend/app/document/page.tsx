'use client'

import { Suspense, useEffect, useRef, useState, useCallback } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'

type DiffType = 'equal' | 'insert' | 'delete' | 'replace'

interface DocumentSummary {
  document_id: string
  topic: string
  mode?: string
  status: string
  current_version: number
  final_version?: number | null
  updated_at: string
  finished_at?: string | null
}

interface Document {
  document_id: string
  version: number
  text: string
  timestamp: string
  topic?: string
  mode?: string
  status?: string
  max_edits?: number
  max_edits_per_agent?: number
  token_budget?: number
  token_used?: number
  finished_at?: string | null
  final_version?: number | null
  total_versions?: number
  agent_count?: number
  agent_roles?: AgentRole[]
}

interface Edit {
  edit_id: string
  document_id?: string
  agent_id: string
  operation: string
  status: string
  tokens_used: number
  created_at: string
}

interface VersionItem {
  version: number
  timestamp: string
}

interface DiffSegment {
  type: DiffType
  text: string
}

interface AgentRole {
  role_key: string
  name: string
  prompt: string
}

interface VersionDiff {
  document_id: string
  target_version: number
  base_version?: number | null
  timestamp: string
  segments: DiffSegment[]
  target_text: string
}

type TabKey = 'text' | 'versions'

const statusStyles: Record<string, string> = {
  active: 'bg-green-100 text-green-800',
  completed: 'bg-blue-100 text-blue-800',
  stopped: 'bg-red-100 text-red-800',
  finalized: 'bg-purple-100 text-purple-800',
}

const hashString = (value: string) =>
  value.split('').reduce((acc, char) => ((acc * 31 + char.charCodeAt(0)) >>> 0), 7)

const getRoleForAgent = (agentId: string, roles?: AgentRole[] | null) => {
  if (!roles || roles.length === 0) return null
  const index = hashString(agentId) % roles.length
  return roles[index]
}

function DocumentPageContent() {
  const searchParams = useSearchParams()
  const queryDocumentId = searchParams.get('documentId')

  const ERROR_MESSAGES = {
    document: 'Не удалось загрузить документ',
    edits: 'Не удалось загрузить правки',
    versions: 'Не удалось загрузить версии',
    generic: 'Произошла ошибка при загрузке документа',
  }

  const [documents, setDocuments] = useState<DocumentSummary[]>([])
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(queryDocumentId)
  const [document, setDocument] = useState<Document | null>(null)
  const [edits, setEdits] = useState<Edit[]>([])
  const [versions, setVersions] = useState<VersionItem[]>([])
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null)
  const [versionDiff, setVersionDiff] = useState<VersionDiff | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingDiff, setLoadingDiff] = useState(false)
  const [error, setError] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [activeTab, setActiveTab] = useState<TabKey>('text')
  const [statusNotice, setStatusNotice] = useState('')

  const selectedVersionRef = useRef<number | null>(null)
  const previousStatusRef = useRef<string | null>(null)
  const selectedVersionMeta = selectedVersion
    ? versions.find((v) => v.version === selectedVersion)
    : undefined

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost'

  const fetchDocuments = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/documents`)
      if (!response.ok) {
        throw new Error('Не удалось получить список документов')
      }
      const data = await response.json()
      setDocuments(data)
      if (!selectedDocumentId && data.length > 0) {
        const targetId = queryDocumentId || data[0].document_id
        setSelectedDocumentId(targetId)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки списка документов')
    }
  }, [API_URL, queryDocumentId, selectedDocumentId])

  const fetchDocument = useCallback(async () => {
    if (!selectedDocumentId) return
    try {
      const response = await fetch(`${API_URL}/api/document/current?document_id=${selectedDocumentId}`)
      if (!response.ok) {
        throw new Error(ERROR_MESSAGES.document)
      }
      const data = await response.json()
      setDocument(data)
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : ERROR_MESSAGES.generic)
    } finally {
      setLoading(false)
    }
  }, [API_URL, ERROR_MESSAGES.document, ERROR_MESSAGES.generic, selectedDocumentId])

  const fetchEdits = useCallback(async () => {
    if (!selectedDocumentId) return
    try {
      const response = await fetch(`${API_URL}/api/edits?limit=200&document_id=${selectedDocumentId}`)
      if (!response.ok) {
        throw new Error(ERROR_MESSAGES.edits)
      }
      const data = await response.json()
      setEdits(data)
    } catch (err) {
      console.error('Error fetching edits:', err)
    }
  }, [API_URL, ERROR_MESSAGES.edits, selectedDocumentId])

  const fetchVersionDiff = useCallback(async (version: number | null) => {
    if (!selectedDocumentId || !version) return
    setLoadingDiff(true)
    try {
      const response = await fetch(`${API_URL}/api/document/${selectedDocumentId}/versions/${version}/diff`)
      if (!response.ok) {
        throw new Error('Failed to fetch diff')
      }
      const data = await response.json()
      setVersionDiff(data)
    } catch (err) {
      console.error('Error fetching diff:', err)
    } finally {
      setLoadingDiff(false)
    }
  }, [API_URL, selectedDocumentId])

  const fetchVersions = useCallback(async (preserveSelection = false) => {
    if (!selectedDocumentId) return
    try {
      const response = await fetch(`${API_URL}/api/document/${selectedDocumentId}/versions?limit=50`)
      if (!response.ok) {
        throw new Error(ERROR_MESSAGES.versions)
      }
      const data: VersionItem[] = await response.json()
      setVersions(data)
      const newestVersion = data[0]?.version ?? null
      const currentSelected = preserveSelection ? selectedVersionRef.current : selectedVersion
      const nextSelected = currentSelected && data.some((v) => v.version === currentSelected)
        ? currentSelected
        : newestVersion
      setSelectedVersion(nextSelected)
      if (nextSelected) {
        fetchVersionDiff(nextSelected)
      } else {
        setVersionDiff(null)
      }
    } catch (err) {
      console.error('Error fetching versions:', err)
    }
  }, [API_URL, ERROR_MESSAGES.versions, selectedDocumentId, selectedVersion, fetchVersionDiff])

  const fetchVersionDiff = useCallback(async (version: number | null) => {
    if (!selectedDocumentId || !version) return
    setLoadingDiff(true)
    try {
      const response = await fetch(`${API_URL}/api/document/${selectedDocumentId}/versions/${version}/diff`)
      if (!response.ok) {
        throw new Error('Failed to fetch diff')
      }
      const data = await response.json()
      setVersionDiff(data)
    } catch (err) {
      console.error('Error fetching diff:', err)
    } finally {
      setLoadingDiff(false)
    }
  }, [API_URL, selectedDocumentId])

  const handleStopAgents = async () => {
    if (!selectedDocumentId) return
    await fetch(`${API_URL}/api/document/${selectedDocumentId}/stop`, { method: 'POST' })
    fetchDocument()
  }

  const handleVersionStep = (step: number) => {
    if (!versions.length || selectedVersion === null) return
    const maxVersion = versions[0].version
    const minVersion = versions[versions.length - 1].version
    const nextVersion = Math.min(Math.max(selectedVersion + step, minVersion), maxVersion)
    setSelectedVersion(nextVersion)
    fetchVersionDiff(nextVersion)
  }

  useEffect(() => {
    selectedVersionRef.current = selectedVersion
  }, [selectedVersion])

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    // Run once on mount to populate available documents
    fetchDocuments()
  }, [])

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (selectedDocumentId) {
      setSelectedVersion(null)
      selectedVersionRef.current = null
      setVersionDiff(null)
      fetchDocument()
      fetchEdits()
      fetchVersions()
    }
  }, [selectedDocumentId])

  useEffect(() => {
    const statusChangedToInactive =
      document?.status &&
      previousStatusRef.current &&
      previousStatusRef.current !== document.status &&
      document.status !== 'active'

    if (statusChangedToInactive) {
      setStatusNotice(`Работа завершена: ${document.status}`)
    }
    previousStatusRef.current = document?.status || null
  }, [document?.status])

  useEffect(() => {
    if (autoRefresh && selectedDocumentId) {
      const interval = setInterval(() => {
        fetchDocument()
        fetchEdits()
        fetchVersions(true)
      }, 3000)
      return () => clearInterval(interval)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh, selectedDocumentId])

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

  const statusClass = document?.status ? (statusStyles[document.status] || 'bg-gray-100 text-gray-800') : 'bg-gray-100 text-gray-800'
  const maxVersion = versions[0]?.version ?? 0
  const minVersion = versions[versions.length - 1]?.version ?? 1

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
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Документ</h1>
            {document?.topic && (
              <p className="text-sm text-gray-600 mt-1">
                Тема: {document.topic} {document.mode ? `• Режим: ${document.mode}` : ''}
              </p>
            )}
            {document?.agent_roles && document.agent_roles.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {document.agent_roles.map((role) => (
                  <span key={role.role_key} className="px-2 py-1 bg-indigo-50 text-indigo-700 text-xs rounded-full border border-indigo-100">
                    {role.name}
                  </span>
                ))}
              </div>
            )}
          </div>
          <div className="flex flex-wrap gap-3 items-center">
            <select
              className="px-3 py-2 border border-gray-300 rounded-md text-sm"
              value={selectedDocumentId ?? ''}
              onChange={(e) => setSelectedDocumentId(e.target.value)}
            >
              {documents.map((doc) => (
                <option key={doc.document_id} value={doc.document_id}>
                  {doc.topic} ({doc.document_id.slice(0, 8)}) — {doc.status}
                </option>
              ))}
            </select>
            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${statusClass}`}>
              {document?.status || '—'}
            </span>
            <button
              onClick={handleStopAgents}
              className="px-4 py-2 bg-red-100 text-red-700 rounded-md hover:bg-red-200 text-sm"
              disabled={!selectedDocumentId}
            >
              Остановить агентов
            </button>
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
                fetchVersions(true)
              }}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm"
            >
              Обновить
            </button>
          </div>
        </div>

        {statusNotice && (
          <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
            <p className="text-blue-800">ℹ️ {statusNotice}</p>
          </div>
        )}

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-800">❌ Ошибка: {error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow">
              <div className="flex items-center border-b border-gray-200">
                <button
                  className={`px-4 py-3 text-sm font-semibold ${activeTab === 'text' ? 'text-indigo-600 border-b-2 border-indigo-600' : 'text-gray-500'}`}
                  onClick={() => setActiveTab('text')}
                >
                  Текст
                </button>
                <button
                  className={`px-4 py-3 text-sm font-semibold ${activeTab === 'versions' ? 'text-indigo-600 border-b-2 border-indigo-600' : 'text-gray-500'}`}
                  onClick={() => setActiveTab('versions')}
                >
                  Версии
                </button>
              </div>

              {activeTab === 'text' ? (
                <div className="p-6">
                  {document ? (
                    <>
                      <div className="flex flex-wrap justify-between items-center mb-4">
                        <div>
                          <h2 className="text-xl font-semibold text-gray-900">
                            Версия: {document.version} {document.final_version ? `(финальная: ${document.final_version})` : ''}
                          </h2>
                          <p className="text-sm text-gray-500">
                            {new Date(document.timestamp).toLocaleString('ru-RU')}
                          </p>
                        </div>
                        <div className="text-sm text-gray-600">
                          <p>Правок: {document.total_versions ? document.total_versions - 1 : 0}{document.max_edits ? ` / ${document.max_edits}` : ''}</p>
                          <p>На агента: {document.max_edits_per_agent ?? '—'} · Агенты: {document.agent_count ?? '—'}</p>
                          <p>Токены: {document.token_used ?? 0}{document.token_budget ? ` / ${document.token_budget}` : ''}</p>
                        </div>
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
              ) : (
                <div className="p-6 space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleVersionStep(-1)}
                        disabled={!selectedVersion || selectedVersion <= minVersion}
                        className="px-3 py-2 bg-gray-100 rounded-md disabled:opacity-50"
                      >
                        ←
                      </button>
                      <div className="text-sm font-medium">
                        Версия {selectedVersion ?? '—'} из {maxVersion || '—'}
                      </div>
                      <button
                        onClick={() => handleVersionStep(1)}
                        disabled={!selectedVersion || selectedVersion >= maxVersion}
                        className="px-3 py-2 bg-gray-100 rounded-md disabled:opacity-50"
                      >
                        →
                      </button>
                    </div>
                    <div className="text-sm text-gray-600">
                      {selectedVersion && selectedVersionMeta && (
                        <span>
                          {new Date(selectedVersionMeta.timestamp).toLocaleString('ru-RU')}
                        </span>
                      )}
                    </div>
                  </div>

                  {loadingDiff ? (
                    <div className="py-6 text-center text-gray-500">Загрузка сравнения...</div>
                  ) : versionDiff ? (
                    <div className="space-y-3">
                      <div className="text-sm text-gray-700">
                        Сравнение с версией {versionDiff.base_version ?? 0}. Изменения подсвечены: зелёным — добавлено, жёлтым — исправлено, красным — удалено.
                      </div>
                      <div className="text-sm bg-gray-50 border border-gray-200 rounded-md p-4 whitespace-pre-wrap leading-relaxed">
                        {versionDiff.segments.map((segment, idx) => {
                          const style =
                            segment.type === 'insert'
                              ? 'bg-green-100 text-green-800'
                              : segment.type === 'delete'
                              ? 'bg-red-100 text-red-800 line-through'
                              : segment.type === 'replace'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'text-gray-800'
                          return (
                            <span key={idx} className={`px-0.5 ${style}`}>
                              {segment.text}
                            </span>
                          )
                        })}
                      </div>
                    </div>
                  ) : (
                    <div className="py-6 text-center text-gray-500">Нет данных для сравнения</div>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                История версий и правок
              </h2>
              <div className="text-sm text-gray-600 mb-3">
                Версий: {versions.length}{document?.total_versions ? ` / ${document.total_versions}` : ''}. Ожидается правок: {Math.max((document?.total_versions ?? 1) - 1, 0)}
              </div>
              <div className="space-y-3 max-h-64 overflow-y-auto">
                {versions.length > 0 ? (
                  versions.map((versionItem) => (
                    <div
                      key={versionItem.version}
                      onClick={() => {
                        setSelectedVersion(versionItem.version)
                        fetchVersionDiff(versionItem.version)
                      }}
                      className={`p-3 rounded-md border cursor-pointer transition ${selectedVersion === versionItem.version ? 'border-indigo-300 bg-indigo-50' : 'border-gray-200 bg-gray-50 hover:border-indigo-200'}`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="text-sm font-semibold text-gray-800">Версия {versionItem.version}</div>
                        <div className="text-xs text-gray-500">
                          {new Date(versionItem.timestamp).toLocaleString('ru-RU')}
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-gray-500 text-center py-4">
                    Пока нет версий
                  </p>
                )}
              </div>

              <div className="mt-5 pt-4 border-t border-gray-200">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-gray-800">Последние правки</h3>
                  <span className="text-xs text-gray-500">Показаны до {edits.length} записей</span>
                </div>
                <div className="space-y-3 max-h-64 overflow-y-auto">
                  {edits.length > 0 ? (
                    edits.map((edit) => {
                      const resolvedRole = getRoleForAgent(edit.agent_id, document?.agent_roles)
                      return (
                        <div
                          key={edit.edit_id}
                          className="p-3 bg-gray-50 rounded-md border border-gray-200"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <div className="text-xs font-medium text-gray-600 flex flex-col gap-1">
                              <span>{edit.agent_id.substring(0, 12)}...</span>
                              {resolvedRole && <span className="inline-flex px-2 py-1 rounded bg-indigo-100 text-indigo-700">{resolvedRole.name}</span>}
                            </div>
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
                      )
                    })
                  ) : (
                    <p className="text-sm text-gray-500 text-center py-4">
                      Пока нет правок
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default function DocumentPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Загрузка документа...</p>
          </div>
        </div>
      }
    >
      <DocumentPageContent />
    </Suspense>
  )
}
