'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  Circle,
  ClipboardList,
  FilePlus2,
  Loader2,
  Play,
  PlugZap,
  RefreshCw,
  RotateCcw,
  Send,
  Square,
  TestTube2,
  XCircle,
} from 'lucide-react'
import { Toaster, toast } from 'sonner'

import { ApprovalBanner } from '@/features/agent/approval-banner'
import { ToolCallItem } from '@/features/agent/tool-call-item'
import { useAgentStore } from '@/store/agent-store'
import { api } from '@/lib/api-client'
import { useAgentEvents } from '@/lib/sse-hooks'
import type { MessageResponse, Project, SSEEvent } from '@/lib/api-types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

type ArtifactRuntimeEvent = Extract<SSEEvent, { type: 'artifact_created' }>
type FixtureFile = {
  name: string
  role: 'order_info' | 'exposure_info' | 'activity_timeline'
  content: string
}

const quickPrompts = [
  {
    label: 'State check',
    text: 'Check this project state and tell me what agent analysis actions are available next.',
  },
  {
    label: 'Validate data',
    text: 'Please validate the uploaded data and explain any blockers before running analysis.',
  },
  {
    label: 'Build panel',
    text: 'Build the category day panel if the required data is ready, then summarize the result.',
  },
  {
    label: 'Full pipeline',
    text: 'Run the full promotion analysis pipeline and report every tool action you take.',
  },
  {
    label: 'Report draft',
    text: 'Generate a business analysis report draft from the latest available artifacts.',
  },
]

const statusStyles = {
  idle: 'border-gray-200 bg-gray-50 text-gray-700',
  ok: 'border-green-200 bg-green-50 text-green-700',
  warn: 'border-amber-200 bg-amber-50 text-amber-800',
  error: 'border-red-200 bg-red-50 text-red-700',
}

const fixtureDates = [
  '2026-03-20',
  '2026-03-21',
  '2026-03-22',
  '2026-03-23',
  '2026-03-24',
  '2026-03-25',
  '2026-03-26',
  '2026-03-27',
  '2026-03-28',
  '2026-03-29',
]

const fixtureCategories = [
  { id: 'cat_snacks', name: 'Snacks', sku: 'sku_snacks', baseGmv: 1280, baseViews: 920, lift: 1.34 },
  { id: 'cat_dairy', name: 'Dairy', sku: 'sku_dairy', baseGmv: 1040, baseViews: 760, lift: 1.18 },
  { id: 'cat_beverage', name: 'Beverage', sku: 'sku_beverage', baseGmv: 860, baseViews: 640, lift: 1.05 },
]

const activityDatesByCategory: Record<string, Set<string>> = {
  cat_snacks: new Set(['2026-03-26', '2026-03-27', '2026-03-28']),
  cat_dairy: new Set(['2026-03-26', '2026-03-27']),
  cat_beverage: new Set(['2026-03-27']),
}

function csvValue(value: string | number | boolean) {
  const text = String(value)
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

function csvLine(values: Array<string | number | boolean>) {
  return values.map(csvValue).join(',')
}

function buildFixtureFiles(): FixtureFile[] {
  const orderRows = [
    csvLine([
      'order_id',
      'user_id',
      'sku_id',
      'category_id',
      'category_name',
      'date',
      'gmv',
      'discount_amount',
      'quantity',
      'order_count',
    ]),
  ]
  const exposureRows = [
    csvLine(['sku_id', 'category_id', 'category_name', 'date', 'view_uv', 'buy_uv', 'exposure_pv']),
  ]
  const activityRows = [
    csvLine(['category_id', 'category_name', 'date', 'activity_name', 'payday']),
  ]

  fixtureDates.forEach((date, dateIndex) => {
    fixtureCategories.forEach((category, categoryIndex) => {
      const isActivity = activityDatesByCategory[category.id]?.has(date) || false
      const trend = 1 + dateIndex * 0.012 + categoryIndex * 0.015
      const gmv = Math.round(category.baseGmv * trend * (isActivity ? category.lift : 1))
      const views = Math.round(category.baseViews * trend * (isActivity ? 1.22 : 1))
      const discount = Math.round(gmv * (isActivity ? 0.12 : 0.035))
      const buyUv = Math.max(1, Math.round(views * (isActivity ? 0.12 : 0.085)))
      const orderCount = Math.max(1, Math.round(gmv / 82))
      const quantity = Math.max(1, Math.round(orderCount * 1.4))

      orderRows.push(
        csvLine([
          `ord_${date.replace(/-/g, '')}_${categoryIndex}`,
          `user_${categoryIndex}_${dateIndex}`,
          category.sku,
          category.id,
          category.name,
          date,
          gmv,
          discount,
          quantity,
          orderCount,
        ])
      )
      exposureRows.push(
        csvLine([
          category.sku,
          category.id,
          category.name,
          date,
          views,
          buyUv,
          views * 3,
        ])
      )
      if (isActivity) {
        activityRows.push(
          csvLine([
            category.id,
            category.name,
            date,
            date === '2026-03-27' ? 'Payday Flash Sale' : 'Spring Promo',
            date === '2026-03-27',
          ])
        )
      }
    })
  })

  return [
    { name: 'order_info.csv', role: 'order_info', content: `${orderRows.join('\n')}\n` },
    { name: 'exposure_info.csv', role: 'exposure_info', content: `${exposureRows.join('\n')}\n` },
    { name: 'activity_timeline.csv', role: 'activity_timeline', content: `${activityRows.join('\n')}\n` },
  ]
}

function formatTime(value?: string) {
  if (!value) return '-'
  return new Date(value).toLocaleTimeString()
}

function truncate(value: string, maxLength = 72) {
  return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value
}

export function AgentAnalysisTestHarness() {
  const {
    messageQueue,
    isRunning,
    error,
    currentSession,
    toolCalls,
    approvalRequests,
    jobs,
    selectedToolCall,
    sendMessage,
    loadPendingApprovals,
    handleSSEEvent,
    interruptSession,
    clearMessages,
    failRun,
    selectToolCall,
    approveApproval: approveApprovalInStore,
    rejectApproval: rejectApprovalInStore,
    setCurrentSession,
  } = useAgentStore()

  const [projects, setProjects] = useState<Project[]>([])
  const [projectsLoading, setProjectsLoading] = useState(false)
  const [projectError, setProjectError] = useState<string | null>(null)
  const [projectId, setProjectId] = useState('')
  const [manualProjectId, setManualProjectId] = useState('')
  const [newProjectName, setNewProjectName] = useState('Agent Analysis Test')
  const [input, setInput] = useState(quickPrompts[0].text)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [turnId, setTurnId] = useState<string | null>(null)
  const [messageResponse, setMessageResponse] = useState<MessageResponse | null>(null)
  const [runtimeEvents, setRuntimeEvents] = useState<SSEEvent[]>([])
  const [artifactEvents, setArtifactEvents] = useState<ArtifactRuntimeEvent[]>([])
  const [localError, setLocalError] = useState<string | null>(null)
  const [seenEventStream, setSeenEventStream] = useState(false)
  const [seenFinalAnswer, setSeenFinalAnswer] = useState(false)
  const [apiBaseUrl] = useState(() => api.getBaseUrl())
  const [fixtureLoading, setFixtureLoading] = useState(false)
  const [fixtureStatus, setFixtureStatus] = useState<string | null>(null)

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === projectId),
    [projectId, projects]
  )

  const allToolCalls = useMemo(() => Object.values(toolCalls).flat(), [toolCalls])
  const jobList = useMemo(() => Object.values(jobs), [jobs])
  const latestEvents = runtimeEvents.slice(0, 12)

  const resetRuntimeState = useCallback(() => {
    clearMessages()
    setCurrentSession(null)
    selectToolCall(null)
    setSessionId(null)
    setTurnId(null)
    setMessageResponse(null)
    setRuntimeEvents([])
    setArtifactEvents([])
    setLocalError(null)
    setSeenEventStream(false)
    setSeenFinalAnswer(false)
  }, [clearMessages, selectToolCall, setCurrentSession])

  const loadProjects = useCallback(async () => {
    setProjectsLoading(true)
    setProjectError(null)
    const response = await api.listProjects()
    if (response.ok && response.data) {
      setProjects(response.data)
      setProjectId((current) => current || response.data?.[0]?.id || '')
    } else {
      setProjectError(response.error || 'Failed to load projects')
    }
    setProjectsLoading(false)
  }, [])

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadProjects()
    }, 0)

    return () => window.clearTimeout(timeout)
  }, [loadProjects])

  const handleProjectChange = (nextProjectId: string) => {
    setProjectId(nextProjectId)
    setManualProjectId(nextProjectId)
    setFixtureStatus(null)
    resetRuntimeState()
  }

  const createTestProject = async () => {
    const name = newProjectName.trim() || 'Agent Analysis Test'
    setProjectsLoading(true)
    setProjectError(null)
    const response = await api.createProject(
      name,
      'promo_analysis',
      'Created from the standalone agent analysis test harness.'
    )
    if (response.ok && response.data) {
      setProjects((current) => [response.data as Project, ...current])
      handleProjectChange(response.data.id)
      toast.success('Test project created')
    } else {
      setProjectError(response.error || 'Failed to create project')
    }
    setProjectsLoading(false)
  }

  const uploadFixtureData = async () => {
    const targetProjectId = projectId.trim()
    if (!targetProjectId) {
      setLocalError('Select or create a project before uploading fixture data.')
      return
    }

    setFixtureLoading(true)
    setFixtureStatus(null)
    setLocalError(null)
    try {
      const files = buildFixtureFiles()
      for (const item of files) {
        const file = new File([item.content], item.name, { type: 'text/csv' })
        const response = await api.uploadFile(targetProjectId, file, item.role)
        if (!response.ok) {
          throw new Error(response.error || `Failed to upload ${item.name}`)
        }
      }
      setFixtureStatus(`Uploaded ${files.length} fixture CSVs`)
      toast.success('Fixture data uploaded')
    } catch (uploadError) {
      const message = uploadError instanceof Error ? uploadError.message : 'Failed to upload fixture data'
      setFixtureStatus(message)
      setLocalError(message)
    } finally {
      setFixtureLoading(false)
    }
  }

  const recordRuntimeEvent = useCallback(
    (event: SSEEvent) => {
      setSeenEventStream(true)
      setRuntimeEvents((current) => [event, ...current].slice(0, 80))
      if (event.type === 'artifact_created') {
        setArtifactEvents((current) => [event, ...current].slice(0, 20))
      }
      if (event.type === 'final_answer') {
        setSeenFinalAnswer(true)
      }
      if (event.type === 'error' || event.type === 'runtime_error') {
        setLocalError(event.error)
      }
    },
    []
  )

  const handleRuntimeEvent = useCallback(
    (event: SSEEvent) => {
      recordRuntimeEvent(event)
      handleSSEEvent(event)
    },
    [handleSSEEvent, recordRuntimeEvent]
  )

  const handleSSEError = useCallback(
    (eventError: Error) => {
      setLocalError(eventError.message)
      failRun(eventError.message)
    },
    [failRun]
  )

  const { connected, error: sseError, reconnect } = useAgentEvents(sessionId, turnId, {
    onEvent: handleRuntimeEvent,
    onError: handleSSEError,
  })

  useEffect(() => {
    if (projectId && sessionId) {
      void loadPendingApprovals(projectId, sessionId)
    }
  }, [loadPendingApprovals, projectId, sessionId])

  const submitPrompt = async () => {
    const prompt = input.trim()
    if (!prompt || isRunning) return
    if (!projectId.trim()) {
      setLocalError('Select or enter a project id before sending a prompt.')
      return
    }

    setLocalError(null)
    setSeenFinalAnswer(false)
    const response = await sendMessage(projectId.trim(), prompt)
    if (response) {
      setMessageResponse(response)
      setSessionId(response.session_id)
      setTurnId(response.turn_id)
      setInput('')
    }
  }

  const handleInterrupt = () => {
    if (sessionId) {
      void interruptSession(sessionId)
    }
  }

  const handleApproveApproval = useCallback(
    async (approvalId: string) => {
      const events = await approveApprovalInStore(approvalId)
      events.forEach(recordRuntimeEvent)
    },
    [approveApprovalInStore, recordRuntimeEvent]
  )

  const handleRejectApproval = useCallback(
    async (approvalId: string) => {
      const events = await rejectApprovalInStore(approvalId)
      events.forEach(recordRuntimeEvent)
    },
    [recordRuntimeEvent, rejectApprovalInStore]
  )

  const checks = [
    { label: 'Project bound', ok: Boolean(projectId), detail: projectId || 'No project' },
    {
      label: 'Message API',
      ok: Boolean(messageResponse),
      detail: messageResponse ? messageResponse.status : 'Waiting',
    },
    {
      label: 'Event stream',
      ok: connected || seenEventStream,
      detail: connected ? 'Connected' : seenEventStream ? 'Observed' : 'Waiting',
    },
    {
      label: 'Final answer',
      ok: seenFinalAnswer,
      detail: seenFinalAnswer ? 'Observed' : 'Waiting',
    },
    {
      label: 'Tool calls',
      ok: allToolCalls.length > 0,
      detail: `${allToolCalls.length} observed`,
    },
    {
      label: 'Approvals',
      ok: approvalRequests.length > 0,
      detail: `${approvalRequests.length} pending`,
      optional: true,
    },
    {
      label: 'Jobs',
      ok: jobList.length > 0,
      detail: `${jobList.length} observed`,
      optional: true,
    },
    {
      label: 'Artifacts',
      ok: artifactEvents.length > 0,
      detail: `${artifactEvents.length} observed`,
      optional: true,
    },
    {
      label: 'Errors',
      ok: !localError && !error && !sseError,
      detail: localError || error || sseError?.message || 'None',
      inverted: true,
    },
  ]

  return (
    <main className="min-h-screen bg-background text-foreground">
      <Toaster position="top-right" richColors />
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-4 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <TestTube2 className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <h1 className="truncate text-xl font-semibold">Agent Analysis Test Harness</h1>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span>{apiBaseUrl}</span>
                {currentSession?.runtime_provider && (
                  <Badge variant="outline">Runtime: {currentSession.runtime_provider}</Badge>
                )}
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              variant="outline"
              className={
                connected
                  ? 'border-green-300 bg-green-50 text-green-700'
                  : sseError
                    ? 'border-red-300 bg-red-50 text-red-700'
                    : 'border-gray-300 bg-gray-50 text-gray-700'
              }
            >
              <PlugZap className="mr-1 h-3.5 w-3.5" />
              {connected ? 'SSE connected' : sseError ? 'SSE error' : 'SSE idle'}
            </Badge>
            <Button variant="outline" size="sm" onClick={reconnect} disabled={!sessionId}>
              <RefreshCw className="mr-1 h-4 w-4" />
              Reconnect
            </Button>
            {isRunning ? (
              <Button variant="destructive" size="sm" onClick={handleInterrupt} disabled={!sessionId}>
                <Square className="mr-1 h-4 w-4" />
                Interrupt
              </Button>
            ) : (
              <Button variant="outline" size="sm" onClick={resetRuntimeState}>
                <RotateCcw className="mr-1 h-4 w-4" />
                Reset
              </Button>
            )}
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1500px] gap-4 px-4 py-4 xl:grid-cols-[360px_minmax(0,1fr)_420px]">
        <aside className="space-y-4">
          <section className="rounded-md border bg-card p-4">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h2 className="text-sm font-semibold">Project</h2>
              <Button variant="ghost" size="sm" onClick={loadProjects} disabled={projectsLoading}>
                {projectsLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
              </Button>
            </div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground" htmlFor="project-list">
              Existing project
            </label>
            <select
              id="project-list"
              value={projectId}
              onChange={(event) => handleProjectChange(event.target.value)}
              className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">Select project</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name} ({project.id})
                </option>
              ))}
            </select>
            <div className="mt-3 grid gap-2">
              <label className="text-xs font-medium text-muted-foreground" htmlFor="manual-project-id">
                Manual project id
              </label>
              <div className="flex gap-2">
                <Input
                  id="manual-project-id"
                  value={manualProjectId}
                  onChange={(event) => setManualProjectId(event.target.value)}
                  placeholder="proj_..."
                />
                <Button
                  variant="outline"
                  onClick={() => handleProjectChange(manualProjectId.trim())}
                  disabled={!manualProjectId.trim()}
                >
                  <Play className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <div className="mt-4 grid gap-2 border-t pt-4">
              <label className="text-xs font-medium text-muted-foreground" htmlFor="new-project-name">
                New test project
              </label>
              <Input
                id="new-project-name"
                value={newProjectName}
                onChange={(event) => setNewProjectName(event.target.value)}
              />
              <Button onClick={createTestProject} disabled={projectsLoading}>
                <FilePlus2 className="mr-2 h-4 w-4" />
                Create Project
              </Button>
            </div>
            <div className="mt-4 grid gap-2 border-t pt-4">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <div className="text-xs font-medium text-muted-foreground">Fixture data</div>
                  {fixtureStatus && (
                    <div className="mt-1 text-xs text-muted-foreground">{fixtureStatus}</div>
                  )}
                </div>
                <Button
                  variant="outline"
                  onClick={uploadFixtureData}
                  disabled={!projectId.trim() || fixtureLoading}
                >
                  {fixtureLoading ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <FilePlus2 className="mr-2 h-4 w-4" />
                  )}
                  Upload CSVs
                </Button>
              </div>
            </div>
            {selectedProject && (
              <dl className="mt-4 space-y-2 rounded-md border bg-background p-3 text-xs">
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Name</dt>
                  <dd className="truncate font-medium">{selectedProject.name}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Status</dt>
                  <dd>{selectedProject.status}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Created</dt>
                  <dd>{formatTime(selectedProject.created_at)}</dd>
                </div>
              </dl>
            )}
            {projectError && (
              <p className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {projectError}
              </p>
            )}
          </section>

          <section className="rounded-md border bg-card p-4">
            <div className="mb-3 flex items-center gap-2">
              <ClipboardList className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-semibold">Observed Contract</h2>
            </div>
            <div className="space-y-2">
              {checks.map((check) => {
                const isHealthy = check.inverted ? check.ok : check.ok
                const CheckIcon = isHealthy ? CheckCircle2 : check.optional ? Circle : XCircle
                const style = isHealthy
                  ? statusStyles.ok
                  : check.optional
                    ? statusStyles.idle
                    : statusStyles.warn
                return (
                  <div
                    key={check.label}
                    className={`flex items-start justify-between gap-3 rounded-md border px-3 py-2 ${style}`}
                  >
                    <div className="flex min-w-0 items-start gap-2">
                      <CheckIcon className="mt-0.5 h-4 w-4 shrink-0" />
                      <div className="min-w-0">
                        <div className="text-sm font-medium">{check.label}</div>
                        <div className="truncate text-xs opacity-80">{check.detail}</div>
                      </div>
                    </div>
                    {check.optional && !check.ok && (
                      <span className="shrink-0 text-xs opacity-70">Optional</span>
                    )}
                  </div>
                )
              })}
            </div>
          </section>
        </aside>

        <section className="flex min-h-[760px] flex-col rounded-md border bg-card">
          <div className="border-b p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-sm font-semibold">Prompt Runner</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  Session {sessionId ? truncate(sessionId, 34) : '-'} / Turn {turnId ? truncate(turnId, 34) : '-'}
                </p>
              </div>
              <Badge variant={isRunning ? 'default' : 'outline'}>
                {isRunning ? 'Running' : 'Ready'}
              </Badge>
            </div>
            <div className="flex flex-wrap gap-2">
              {quickPrompts.map((prompt) => (
                <Button
                  key={prompt.label}
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setInput(prompt.text)}
                >
                  <Bot className="mr-1 h-4 w-4" />
                  {prompt.label}
                </Button>
              ))}
            </div>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {messageQueue.length === 0 ? (
              <div className="flex h-full min-h-[320px] items-center justify-center rounded-md border border-dashed bg-background text-center">
                <div className="max-w-md px-6">
                  <Bot className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
                  <p className="text-sm font-medium">No runtime messages yet</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Choose a project, submit a prompt, and watch backend events arrive here.
                  </p>
                </div>
              </div>
            ) : (
              messageQueue.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <article
                    className={`max-w-[86%] rounded-md border px-4 py-3 text-sm ${
                      message.role === 'user'
                        ? 'border-primary/50 bg-primary/15'
                        : 'bg-background'
                    }`}
                  >
                    <div className="mb-1 flex items-center justify-between gap-3 text-xs text-muted-foreground">
                      <span className="font-medium uppercase">{message.role}</span>
                      <span>{formatTime(message.created_at)}</span>
                    </div>
                    <div className="whitespace-pre-wrap leading-6">{message.content}</div>
                  </article>
                </div>
              ))
            )}
            {isRunning && (
              <div className="flex items-center gap-2 rounded-md border bg-background px-4 py-3 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Agent runtime is processing
              </div>
            )}
          </div>

          <div className="border-t p-4">
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  void submitPrompt()
                }
              }}
              disabled={isRunning}
              rows={4}
              className="min-h-24 w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-60"
              placeholder="Enter an agent analysis prompt"
            />
            <div className="mt-3 flex items-center justify-between gap-3">
              <div className="min-w-0 text-xs text-muted-foreground">
                Natural language is sent through <span className="font-mono">POST /api/agent/messages</span>.
              </div>
              <Button onClick={submitPrompt} disabled={!input.trim() || !projectId || isRunning}>
                <Send className="mr-2 h-4 w-4" />
                Send
              </Button>
            </div>
          </div>
        </section>

        <aside className="space-y-4">
          {(localError || error || sseError) && (
            <section className="rounded-md border border-red-200 bg-red-50 p-4 text-red-800">
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
                <AlertCircle className="h-4 w-4" />
                Runtime Error
              </div>
              <p className="text-sm">{localError || error || sseError?.message}</p>
            </section>
          )}

          {approvalRequests.length > 0 && (
            <section className="space-y-2 rounded-md border bg-card p-4">
              <h2 className="text-sm font-semibold">Approvals</h2>
              {approvalRequests.map((approval) => (
                <ApprovalBanner
                  key={approval.id}
                  approval={approval}
                  onApprove={handleApproveApproval}
                  onReject={handleRejectApproval}
                />
              ))}
            </section>
          )}

          <section className="rounded-md border bg-card p-4">
            <h2 className="mb-3 text-sm font-semibold">Tool Calls</h2>
            {allToolCalls.length === 0 ? (
              <p className="rounded-md border border-dashed bg-background px-3 py-6 text-center text-sm text-muted-foreground">
                No tool calls observed
              </p>
            ) : (
              <div className="space-y-2">
                {allToolCalls.map((toolCall, index) => (
                  <ToolCallItem
                    key={`${toolCall.turnId}_${toolCall.id}_${index}`}
                    toolCall={toolCall}
                    isSelected={selectedToolCall?.id === toolCall.id}
                    onSelect={selectToolCall}
                  />
                ))}
              </div>
            )}
            {selectedToolCall && (
              <div className="mt-3 rounded-md border bg-background p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <h3 className="text-xs font-semibold uppercase text-muted-foreground">
                    Selected Payload
                  </h3>
                  <Button variant="ghost" size="sm" onClick={() => selectToolCall(null)}>
                    Clear
                  </Button>
                </div>
                <pre className="max-h-56 overflow-auto rounded-md bg-muted p-2 text-xs">
                  {JSON.stringify(selectedToolCall.payload, null, 2)}
                </pre>
              </div>
            )}
          </section>

          <section className="rounded-md border bg-card p-4">
            <h2 className="mb-3 text-sm font-semibold">Jobs</h2>
            {jobList.length === 0 ? (
              <p className="rounded-md border border-dashed bg-background px-3 py-6 text-center text-sm text-muted-foreground">
                No jobs observed
              </p>
            ) : (
              <div className="space-y-3">
                {jobList.map((job) => (
                  <div key={job.id} className="rounded-md border bg-background p-3">
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium">{job.action || job.id}</div>
                        <div className="truncate text-xs text-muted-foreground">{job.message}</div>
                      </div>
                      <Badge variant="outline">{job.status || 'running'}</Badge>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full bg-primary"
                        style={{ width: `${Math.round(job.progress * 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-md border bg-card p-4">
            <h2 className="mb-3 text-sm font-semibold">Artifacts</h2>
            {artifactEvents.length === 0 ? (
              <p className="rounded-md border border-dashed bg-background px-3 py-6 text-center text-sm text-muted-foreground">
                No artifact events observed
              </p>
            ) : (
              <div className="space-y-2">
                {artifactEvents.map((artifact) => (
                  <div key={`${artifact.turn_id}_${artifact.artifact_id}`} className="rounded-md border bg-background p-3">
                    <div className="text-sm font-medium">{artifact.name}</div>
                    <div className="mt-1 font-mono text-xs text-muted-foreground">{artifact.artifact_id}</div>
                    {artifact.path && (
                      <div className="mt-1 truncate text-xs text-muted-foreground">{artifact.path}</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-md border bg-card p-4">
            <h2 className="mb-3 text-sm font-semibold">Latest SSE Events</h2>
            {latestEvents.length === 0 ? (
              <p className="rounded-md border border-dashed bg-background px-3 py-6 text-center text-sm text-muted-foreground">
                No events observed
              </p>
            ) : (
              <div className="space-y-2">
                {latestEvents.map((event, index) => (
                  <details key={`${event.type}_${event.turn_id}_${index}`} className="rounded-md border bg-background p-3">
                    <summary className="cursor-pointer text-sm font-medium">{event.type}</summary>
                    <pre className="mt-2 max-h-52 overflow-auto rounded-md bg-muted p-2 text-xs">
                      {JSON.stringify(event, null, 2)}
                    </pre>
                  </details>
                ))}
              </div>
            )}
          </section>
        </aside>
      </div>
    </main>
  )
}
