'use client'

import Link from 'next/link'
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useParams } from 'next/navigation'
import { Toaster, toast } from 'sonner'
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  Check,
  CheckCircle2,
  Clipboard,
  Clock3,
  Copy,
  FileBarChart,
  Loader2,
  MessageSquare,
  MessageSquarePlus,
  Paperclip,
  RefreshCw,
  Send,
  Sparkles,
  Square,
  ThumbsUp,
  Timer,
  Trash2,
  Wand2,
  X,
  XCircle,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { MarkdownView } from '@/components/markdown-view'
import { useApiBaseHref } from '@/lib/use-api-base-href'
import { api } from '@/lib/api-client'
import { useAgentEvents } from '@/lib/sse-hooks'
import type { AgentMessage, AgentSession, SSEEvent } from '@/lib/api-types'
import { useAgentStore, type ApprovalRequest, type JobStatus, type ThoughtEntry, type ToolCall } from '@/store/agent-store'
import { useProjectStore } from '@/store/project-store'
import type { AgentRunStatus, ArtifactPreview, PlanStep, PlanStepStatus } from '@/types/agent'

type ArtifactEvent = Extract<SSEEvent, { type: 'artifact_created' }>

const quickPrompts = [
  '分析本次活动对 GMV 的真实增量影响',
  '比较曝光资源和折扣资源哪个更有效',
  '识别最值得优先加码的品类',
  '生成下一轮活动的资源配置建议',
]

const statusText: Record<AgentRunStatus, string> = {
  idle: '未开始',
  planning: '正在规划',
  waiting_approval: '等待确认',
  running: '执行中',
  completed: '已完成',
  failed: '失败',
}

const statusClass: Record<AgentRunStatus, string> = {
  idle: 'border-gray-200 bg-gray-50 text-gray-700',
  planning: 'border-blue-200 bg-blue-50 text-blue-700',
  waiting_approval: 'border-amber-200 bg-amber-50 text-amber-800',
  running: 'border-green-200 bg-green-50 text-green-700',
  completed: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  failed: 'border-red-200 bg-red-50 text-red-700',
}

const planStepTemplates: Array<Omit<PlanStep, 'status'>> = [
  { id: 'validate', title: '数据校验', description: '检查订单、曝光和活动窗口完整性', toolName: 'data.validate' },
  { id: 'pipeline', title: '执行分析管道', description: '运行 panel、LocalGap、DID 和策略分层', toolName: 'analysis.run_full_pipeline' },
  { id: 'results', title: '读取最新结果', description: '汇总 artifact 和可解释指标', toolName: 'result.get_latest' },
  { id: 'answer', title: '生成解释与建议', description: '输出下一轮资源配置动作', toolName: 'final_answer' },
]

const pipelineActions = new Set([
  'analysis.run_full_pipeline',
  'panel.build_category_day',
  'analysis.run_diagnostics',
  'analysis.run_psm_did',
  'analysis.run_localgap',
  'analysis.run_gps_uplift',
  'chart.render',
  'chart.render_dashboard',
  'report.generate',
])

function useAgentResponsiveDensity() {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const element = containerRef.current
    if (!element) return

    let frame = 0

    const setDensity = (nextDensity: number) => {
      const density = clampNumber(nextDensity, 0, 1)
      element.style.setProperty('--agent-density', density.toFixed(3))
      element.dataset.agentDensity =
        density <= 0.02 ? 'minimum' : density < 0.45 ? 'dense' : density < 0.8 ? 'compact' : 'comfortable'
    }

    const updateDensity = () => {
      window.cancelAnimationFrame(frame)
      frame = window.requestAnimationFrame(() => {
        const height = element.clientHeight || window.innerHeight
        const width = element.clientWidth || window.innerWidth
        let density = clampNumber(Math.min((height - 680) / 360, (width - 920) / 420), 0, 1)

        setDensity(density)

        const inspector = element.querySelector<HTMLElement>('.agent-side-inspector')
        if (!inspector?.clientHeight) return

        for (let attempt = 0; attempt < 6; attempt += 1) {
          const overflowRatio = inspector.scrollHeight / inspector.clientHeight
          if (overflowRatio <= 1) break

          density = clampNumber(density - Math.min(0.25, (overflowRatio - 1) * 1.7), 0, 1)
          setDensity(density)
        }
      })
    }

    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(updateDensity)
    observer?.observe(element)
    window.addEventListener('resize', updateDensity)
    updateDensity()

    return () => {
      window.cancelAnimationFrame(frame)
      observer?.disconnect()
      window.removeEventListener('resize', updateDensity)
    }
  }, [])

  return containerRef
}

function clampNumber(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function buildPlanSteps({
  toolCalls,
  approvals,
  jobs,
  artifacts,
  runStatus,
  isRunning,
}: {
  toolCalls: ToolCall[]
  approvals: ApprovalRequest[]
  jobs: JobStatus[]
  artifacts: ArtifactPreview[]
  runStatus: AgentRunStatus
  isRunning: boolean
}): PlanStep[] {
  const hasApproval = approvals.some((approval) => approval.action === 'analysis.run_full_pipeline')
  const hasSucceededJob = jobs.some((job) => job.status === 'succeeded')
  const hasFailedJob = jobs.some((job) => job.status === 'failed')
  const hasRunningJob = jobs.some((job) => job.status === 'running')

  const byAction = (action: string) => toolCalls.filter((toolCall) => toolCall.action === action)
  const hasStatus = (calls: ToolCall[], statuses: ToolCall['status'][]) =>
    calls.some((toolCall) => statuses.includes(toolCall.status))

  const validateCalls = byAction('data.validate')
  const resultCalls = byAction('result.get_latest')
  const pipelineCalls = toolCalls.filter((toolCall) => pipelineActions.has(toolCall.action))

  const statusForCalls = (calls: ToolCall[], fallback: PlanStepStatus = 'pending'): PlanStepStatus => {
    if (hasStatus(calls, ['error'])) return 'failed'
    if (hasStatus(calls, ['running'])) return 'running'
    if (hasStatus(calls, ['success'])) return 'completed'
    return fallback
  }

  const validateStatus = statusForCalls(validateCalls)
  let pipelineStatus: PlanStepStatus = statusForCalls(pipelineCalls)
  if (hasFailedJob || hasStatus(pipelineCalls, ['error'])) {
    pipelineStatus = 'failed'
  } else if (hasSucceededJob || hasStatus(byAction('analysis.run_full_pipeline'), ['success'])) {
    pipelineStatus = 'completed'
  } else if (hasRunningJob || (isRunning && hasStatus(pipelineCalls, ['success', 'running']))) {
    pipelineStatus = 'running'
  } else if (hasApproval || hasStatus(byAction('analysis.run_full_pipeline'), ['waiting_approval'])) {
    pipelineStatus = 'pending'
  }

  const resultsStatus =
    statusForCalls(resultCalls, artifacts.length > 0 || hasSucceededJob ? 'completed' : 'pending')
  const answerStatus: PlanStepStatus =
    runStatus === 'failed'
      ? 'failed'
      : runStatus === 'completed'
        ? 'completed'
        : runStatus === 'waiting_approval'
          ? 'pending'
          : isRunning
            ? 'running'
            : 'pending'

  return planStepTemplates.map((step) => {
    const statusById: Record<string, PlanStepStatus> = {
      validate: validateStatus,
      pipeline: pipelineStatus,
      results: resultsStatus,
      answer: answerStatus,
    }

    return {
      ...step,
      description:
        step.id === 'pipeline' && hasApproval
          ? '等待确认后运行 panel、LocalGap、DID 和策略分层'
          : step.description,
      status: statusById[step.id] || 'pending',
    }
  })
}

const AGENT_SESSION_STORAGE_PREFIX = 'baa.agentSession.'

function agentSessionStorageKey(projectId: string) {
  return `${AGENT_SESSION_STORAGE_PREFIX}${projectId}`
}

export function AgentAnalysisPage() {
  const params = useParams<{ project_id: string }>()
  const projectId = params.project_id
  const hrefFor = useApiBaseHref()
  const densityRef = useAgentResponsiveDensity()
  const { currentProject, projectState, files } = useProjectStore()
  const {
    messageQueue,
    isRunning,
    error,
    currentSession,
    toolCalls,
    approvalRequests,
    jobs,
    thoughts,
    sendMessage,
    loadSessionMessages,
    loadPendingApprovals,
    handleSSEEvent,
    interruptSession,
    clearMessages,
    failRun,
    setCurrentSession,
    approveApproval,
    rejectApproval,
  } = useAgentStore()

  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [turnId, setTurnId] = useState<string | null>(null)
  const [artifactEvents, setArtifactEvents] = useState<ArtifactEvent[]>([])
  const [lastCompletedAt, setLastCompletedAt] = useState<string | null>(null)
  const [projectSessions, setProjectSessions] = useState<AgentSession[]>([])
  const [loadingSessions, setLoadingSessions] = useState(false)
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null)
  const artifactEventIdsRef = useRef(new Set<string>())

  const rememberSessionId = useCallback(
    (nextSessionId: string) => {
      if (typeof window === 'undefined') return
      try {
        window.localStorage.setItem(agentSessionStorageKey(projectId), nextSessionId)
      } catch {
        // Ignore storage failures; backend session state still exists.
      }
    },
    [projectId],
  )

  const forgetSessionId = useCallback(() => {
    if (typeof window === 'undefined') return
    try {
      window.localStorage.removeItem(agentSessionStorageKey(projectId))
    } catch {
      // Ignore storage failures.
    }
  }, [projectId])

  const resetConversationState = useCallback(() => {
    clearMessages()
    setCurrentSession(null)
    setSessionId(null)
    setTurnId(null)
    setArtifactEvents([])
    setLastCompletedAt(null)
    artifactEventIdsRef.current.clear()
  }, [clearMessages, setCurrentSession])

  const refreshProjectSessions = useCallback(async () => {
    setLoadingSessions(true)
    const sessionsResponse = await api.listProjectSessions(projectId)
    setLoadingSessions(false)
    if (sessionsResponse.ok && sessionsResponse.data) {
      setProjectSessions(sessionsResponse.data)
    }
    return sessionsResponse.ok ? sessionsResponse.data || [] : []
  }, [projectId])

  useEffect(() => {
    let cancelled = false

    const readStoredSessionId = () => {
      if (typeof window === 'undefined') return null
      try {
        return window.localStorage.getItem(agentSessionStorageKey(projectId))
      } catch {
        return null
      }
    }
    const loadCandidateSession = async (candidateSessionId?: string | null, persist = true) => {
      if (!candidateSessionId) return false
      const sessionResponse = await api.getSession(candidateSessionId)
      if (!sessionResponse.ok || sessionResponse.data?.project_id !== projectId) {
        if (persist) forgetSessionId()
        return false
      }
      if (cancelled) return true
      await loadSessionMessages(candidateSessionId)
      if (cancelled) return true
      setSessionId(candidateSessionId)
      setTurnId(null)
      if (persist) rememberSessionId(candidateSessionId)
      return true
    }

    const restoreSession = async () => {
      resetConversationState()
      const sessions = await refreshProjectSessions()

      if (await loadCandidateSession(readStoredSessionId())) return

      const demoResponse = await api.getDemoStatus()
      if (
        demoResponse.ok &&
        demoResponse.data?.enabled &&
        demoResponse.data.project_id === projectId &&
        demoResponse.data.session_id &&
        await loadCandidateSession(demoResponse.data.session_id)
      ) {
        return
      }

      const latestSession = sessions.find((session) => session.project_id === projectId)
      await loadCandidateSession(latestSession?.id)
    }

    void restoreSession()
    return () => {
      cancelled = true
    }
  }, [forgetSessionId, loadSessionMessages, projectId, refreshProjectSessions, rememberSessionId, resetConversationState])

  useEffect(() => {
    if (sessionId) {
      void loadPendingApprovals(projectId, sessionId)
    }
  }, [projectId, sessionId, loadPendingApprovals])

  const applyRuntimeSideEffects = useCallback(
    (event: SSEEvent) => {
      if (event.type === 'artifact_created') {
        if (!artifactEventIdsRef.current.has(event.artifact_id)) {
          artifactEventIdsRef.current.add(event.artifact_id)
          setArtifactEvents((current) => [event, ...current].slice(0, 8))
          toast.success(`产物已生成：${event.name}`)
        }
      }
      if (event.type === 'final_answer') {
        setLastCompletedAt(new Date().toISOString())
        void refreshProjectSessions()
      }
    },
    [refreshProjectSessions],
  )

  const handleRuntimeEvent = useCallback(
    (event: SSEEvent) => {
      applyRuntimeSideEffects(event)
      handleSSEEvent(event)
    },
    [applyRuntimeSideEffects, handleSSEEvent],
  )

  const handleSSEError = useCallback(
    (eventError: Error) => {
      failRun(eventError.message)
    },
    [failRun],
  )

  const { connected, error: sseError, reconnect } = useAgentEvents(sessionId, turnId, {
    onEvent: handleRuntimeEvent,
    onError: handleSSEError,
  })

  const allToolCalls = useMemo(() => Object.values(toolCalls).flat(), [toolCalls])
  const allThoughts = useMemo(() => Object.values(thoughts).flat(), [thoughts])
  const jobList = useMemo(() => Object.values(jobs), [jobs])
  const activeJob = jobList.find((job) => job.status === 'running') || jobList[0] || null

  const runStatus: AgentRunStatus = error || sseError
    ? 'failed'
    : approvalRequests.length > 0
      ? 'waiting_approval'
      : isRunning
        ? 'running'
        : messageQueue.length > 0
          ? 'completed'
          : 'idle'

  const artifacts: ArtifactPreview[] = artifactEvents.map((event) => ({
    id: event.artifact_id,
    name: event.name,
    type: 'artifact',
    path: event.path,
  }))
  const planSteps = useMemo(
    () =>
      buildPlanSteps({
        toolCalls: allToolCalls,
        approvals: approvalRequests,
        jobs: jobList,
        artifacts,
        runStatus,
        isRunning,
      }),
    [allToolCalls, approvalRequests, artifacts, jobList, runStatus, isRunning],
  )

  async function handleSend(nextInput = input) {
    const prompt = nextInput.trim()
    if (!prompt || isRunning) return

    const response = await sendMessage(projectId, prompt)
    if (response) {
      setSessionId(response.session_id)
      setTurnId(response.turn_id)
      rememberSessionId(response.session_id)
      void refreshProjectSessions()
      setInput('')
    }
  }

  function handleInterrupt() {
    if (sessionId) {
      void interruptSession(sessionId)
    }
  }

  async function handleApprove(approvalId: string) {
    const events = await approveApproval(approvalId)
    events.forEach(applyRuntimeSideEffects)
  }

  async function handleReject(approvalId: string) {
    const events = await rejectApproval(approvalId)
    events.forEach(applyRuntimeSideEffects)
  }

  function handleStartNewThread() {
    if (isRunning) {
      toast.error('当前线程还在运行，完成后再新建线程。')
      return
    }
    resetConversationState()
    forgetSessionId()
  }

  async function handleContinueSession(nextSessionId: string) {
    if (nextSessionId === sessionId) return
    if (isRunning) {
      toast.error('当前线程还在运行，完成后再切换线程。')
      return
    }
    const sessionResponse = await api.getSession(nextSessionId)
    if (!sessionResponse.ok || sessionResponse.data?.project_id !== projectId) {
      toast.error('这个线程已不可用。')
      void refreshProjectSessions()
      return
    }
    resetConversationState()
    await loadSessionMessages(nextSessionId)
    setSessionId(nextSessionId)
    setTurnId(null)
    rememberSessionId(nextSessionId)
    void loadPendingApprovals(projectId, nextSessionId)
  }

  async function handleDeleteSession(targetSessionId: string) {
    if (isRunning && targetSessionId === sessionId) {
      toast.error('当前线程还在运行，完成后再删除。')
      return
    }
    const targetSession = projectSessions.find((session) => session.id === targetSessionId)
    const ok = window.confirm(`确认删除线程${targetSession?.last_message ? `“${targetSession.last_message.slice(0, 24)}”` : ''}？`)
    if (!ok) return

    setDeletingSessionId(targetSessionId)
    const response = await api.deleteSession(targetSessionId)
    setDeletingSessionId(null)
    if (!response.ok) {
      toast.error(response.error || '删除线程失败')
      return
    }

    setProjectSessions((sessions) => sessions.filter((session) => session.id !== targetSessionId))
    if (targetSessionId === sessionId) {
      resetConversationState()
      forgetSessionId()
    }
    toast.success('线程已删除')
  }

  return (
    <div className="h-full overflow-hidden bg-background">
      <Toaster position="top-right" richColors />
      <div ref={densityRef} className="agent-analysis-page flex h-full min-h-0 flex-col overflow-hidden bg-background text-[15px] leading-6">
          <AgentAnalysisHeader
            status={runStatus}
            connected={connected}
            onRefresh={reconnect}
            onStop={handleInterrupt}
            onClear={handleStartNewThread}
            canStop={Boolean(isRunning && sessionId)}
          />

          <div className="agent-analysis-grid grid min-h-0 flex-1 grid-cols-[minmax(0,2fr)_minmax(0,1fr)] overflow-hidden">
            <AgentConversationPanel
              messages={messageQueue}
              toolCalls={allToolCalls}
              planSteps={planSteps}
              runStatus={runStatus}
              thoughts={allThoughts}
              approvals={approvalRequests}
              artifacts={artifacts}
              isRunning={isRunning}
              input={input}
              onInputChange={setInput}
              onSend={() => void handleSend()}
              onPrompt={(prompt) => {
                setInput(prompt)
                void handleSend(prompt)
              }}
              onApprove={handleApprove}
              onReject={handleReject}
              disabled={!projectId}
            />

            <AgentSideInspector
              projectName={currentProject?.name || 'Keemart 促销增长全流程演示 Demo'}
              projectStatus={currentProject?.status || 'report_ready'}
              projectStage={currentProject?.current_stage || 'report_ready'}
              fileCount={files.length || projectState?.files_count || 3}
              artifactCount={projectState?.artifacts_count || artifacts.length || 8}
              sessionProvider={currentSession?.runtime_provider || 'claude_agent_sdk'}
              runStatus={runStatus}
              activeJob={activeJob}
              toolCalls={allToolCalls}
              planSteps={planSteps}
              artifacts={artifacts}
              sessions={projectSessions}
              currentSessionId={sessionId}
              loadingSessions={loadingSessions}
              deletingSessionId={deletingSessionId}
              onNewThread={handleStartNewThread}
              onContinueSession={(nextSessionId) => void handleContinueSession(nextSessionId)}
              onDeleteSession={(targetSessionId) => void handleDeleteSession(targetSessionId)}
              lastCompletedAt={lastCompletedAt}
              dashboardHref={hrefFor(`/projects/${projectId}/dashboard`)}
              reportHref={hrefFor(`/projects/${projectId}/reports`)}
            />
          </div>
        </div>
    </div>
  )
}

function AgentAnalysisHeader({
  status,
  connected,
  canStop,
  onRefresh,
  onStop,
  onClear,
}: {
  status: AgentRunStatus
  connected: boolean
  canStop: boolean
  onRefresh: () => void
  onStop: () => void
  onClear: () => void
}) {
  return (
    <section className="agent-analysis-header flex shrink-0 items-end justify-between">
      <div>
        <div className="flex items-center gap-2 text-[11px] font-semibold text-muted-foreground">
          <span>当前项目</span>
          <ArrowRight className="h-3.5 w-3.5" />
          <span>Agent 分析</span>
        </div>
        <div className="mt-1.5 flex flex-wrap items-center gap-2.5">
          <h1 className="agent-analysis-title font-bold tracking-normal">Agent 分析</h1>
          <Badge variant="outline" className={statusClass[status]}>
            {statusText[status]}
          </Badge>
          <Badge variant="outline" className={connected ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-gray-200 bg-gray-50 text-gray-600'}>
            {connected ? 'SSE 已连接' : 'SSE 待连接'}
          </Badge>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">通过对话驱动数据检查、分析执行与结果解释</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" size="sm" onClick={onRefresh}>
          <RefreshCw className="mr-1.5 h-4 w-4" />
          刷新运行
        </Button>
        <Button variant="outline" size="sm" onClick={onStop} disabled={!canStop}>
          <Square className="mr-1.5 h-4 w-4" />
          停止
        </Button>
        <Button variant="outline" size="sm" onClick={onClear}>
          <MessageSquarePlus className="mr-1.5 h-4 w-4" />
          新建线程
        </Button>
      </div>
    </section>
  )
}
function AgentConversationPanel({
  messages,
  toolCalls,
  planSteps,
  runStatus,
  thoughts,
  approvals,
  artifacts,
  isRunning,
  input,
  disabled,
  onInputChange,
  onSend,
  onPrompt,
  onApprove,
  onReject,
}: {
  messages: AgentMessage[]
  toolCalls: ToolCall[]
  planSteps: PlanStep[]
  runStatus: AgentRunStatus
  thoughts: ThoughtEntry[]
  approvals: ApprovalRequest[]
  artifacts: ArtifactPreview[]
  isRunning: boolean
  input: string
  disabled: boolean
  onInputChange: (value: string) => void
  onSend: () => void
  onPrompt: (prompt: string) => void
  onApprove: (id: string) => void
  onReject: (id: string) => void
}) {
  return (
    <section className="flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-border bg-white shadow-[var(--shadow-soft)]">
      <div className="agent-quick-prompts shrink-0 border-b border-border">
        <div className="flex flex-wrap gap-2">
          {quickPrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => onPrompt(prompt)}
              className="agent-quick-prompt rounded-full border border-border bg-[#fbfcfe] text-xs font-semibold text-[#4b5563] transition hover:border-[#f2cf4a] hover:bg-secondary hover:text-[#1f2937]"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      <ConversationStream
        messages={messages}
        toolCalls={toolCalls}
        planSteps={planSteps}
        runStatus={runStatus}
        thoughts={thoughts}
        approvals={approvals}
        artifacts={artifacts}
        isRunning={isRunning}
        onApprove={onApprove}
        onReject={onReject}
      />

      <AgentMessageComposer
        value={input}
        disabled={disabled || isRunning}
        isRunning={isRunning}
        onChange={onInputChange}
        onSend={onSend}
      />
    </section>
  )
}

function ConversationStream({
  messages,
  toolCalls,
  planSteps,
  runStatus,
  thoughts,
  approvals,
  artifacts,
  isRunning,
  onApprove,
  onReject,
}: {
  messages: AgentMessage[]
  toolCalls: ToolCall[]
  planSteps: PlanStep[]
  runStatus: AgentRunStatus
  thoughts: ThoughtEntry[]
  approvals: ApprovalRequest[]
  artifacts: ArtifactPreview[]
  isRunning: boolean
  onApprove: (id: string) => void
  onReject: (id: string) => void
}) {
  return (
    <div className="agent-conversation-stream flex min-h-0 flex-1 flex-col overflow-y-auto">
      {messages.length === 0 && <SystemNoticeMessage />}

      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}

      {(thoughts.length > 0 || isRunning) && <ThoughtProgressCard thoughts={thoughts} isRunning={isRunning} />}

      {(toolCalls.length > 0 || approvals.length > 0 || artifacts.length > 0) && (
        <div className="ml-8 space-y-3 border-l border-dashed border-border pl-4">
          <AgentPlanCard steps={planSteps} runStatus={runStatus} />
          {toolCalls.slice(-4).map((toolCall) => (
            <ToolCallCard key={`${toolCall.turnId}-${toolCall.id}`} toolCall={toolCall} />
          ))}
          {approvals.map((approval) => (
            <ApprovalRequestCard key={approval.id} approval={approval} onApprove={onApprove} onReject={onReject} />
          ))}
          {artifacts.slice(0, 2).map((artifact) => (
            <ArtifactPreviewCard key={artifact.id} artifact={artifact} />
          ))}
        </div>
      )}

      {isRunning && (
        <div className="flex items-center gap-2 rounded-xl border border-border bg-[#fbfcfe] px-4 py-3 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin text-[#d39a00]" />
          Agent 正在分析项目上下文与工具结果
        </div>
      )}
    </div>
  )
}

function ThoughtProgressCard({ thoughts, isRunning }: { thoughts: ThoughtEntry[]; isRunning: boolean }) {
  const latestThoughts = thoughts.slice(-6)
  return (
    <div className="ml-8 rounded-2xl border border-blue-100 bg-blue-50/60 p-4 text-sm text-blue-950">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 font-bold">
          {isRunning ? (
            <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
          ) : (
            <Sparkles className="h-4 w-4 text-blue-600" />
          )}
          <span>Agent thinking</span>
        </div>
        <Badge variant="outline" className="border-blue-200 bg-white/70 text-blue-700">
          {latestThoughts.length || 1} updates
        </Badge>
      </div>
      <div className="mt-3 max-h-44 space-y-2 overflow-y-auto">
        {latestThoughts.length === 0 ? (
          <p className="text-xs leading-5 text-blue-800/80">
            Preparing a public progress summary while the runtime works.
          </p>
        ) : (
          latestThoughts.map((thought) => (
            <div key={thought.id} className="rounded-xl bg-white/75 px-3 py-2">
              <div className="mb-1 flex items-center justify-between gap-3 text-[11px] uppercase text-blue-700/70">
                <span>{thought.phase || 'thinking'}</span>
                <span>{formatTime(thought.createdAt)}</span>
              </div>
              <p className="whitespace-pre-wrap text-xs leading-5">{thought.content}</p>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function SystemNoticeMessage() {
  return (
    <div className="agent-system-notice rounded-2xl border border-dashed border-[#f2cf4a] bg-secondary/70 text-center">
      <Sparkles className="mx-auto h-6 w-6 text-[#d39a00]" />
      <h2 className="mt-2 text-base font-bold">从一个分析目标开始</h2>
      <p className="mx-auto mt-1 max-w-xl text-sm leading-6 text-muted-foreground">
        输入自然语言问题，Agent 会先读取项目状态，再决定是否校验数据、请求确认、运行分析管道或解释最新结果。
      </p>
    </div>
  )
}

function MessageBubble({ message }: { message: AgentMessage }) {
  const isUser = message.role === 'user'
  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && <Avatar tone="agent" icon={<Bot className="h-4 w-4" />} />}
      <article className={`max-w-[78%] rounded-2xl border px-4 py-3 text-sm shadow-sm ${isUser ? 'border-transparent bg-[#eef4ff]' : 'border-border bg-white'}`}>
        {isUser ? (
          <div className="whitespace-pre-wrap leading-6">{message.content}</div>
        ) : (
          <MarkdownView content={message.content} compact />
        )}
        <div className="mt-2 flex items-center justify-between gap-4 text-[11px] text-muted-foreground">
          <span>{formatTime(message.created_at)}</span>
          {!isUser && (
            <span className="flex items-center gap-1">
              <IconAction label="复制" icon={<Copy className="h-3.5 w-3.5" />} />
              <IconAction label="有用" icon={<ThumbsUp className="h-3.5 w-3.5" />} />
              <IconAction label="重试" icon={<RefreshCw className="h-3.5 w-3.5" />} />
            </span>
          )}
        </div>
      </article>
      {isUser && <Avatar tone="user" label="DA" />}
    </div>
  )
}

function AgentPlanCard({ steps, runStatus }: { steps: PlanStep[]; runStatus: AgentRunStatus }) {
  return (
    <div className="rounded-2xl border border-border bg-[#fbfcfe] p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="rounded-lg bg-secondary p-2 text-[#d39a00]">
            <Clipboard className="h-4 w-4" />
          </span>
          <div>
            <h3 className="text-sm font-bold">Agent 执行计划</h3>
            <p className="text-xs text-muted-foreground">按需调用唯一业务工具 business_analysis</p>
          </div>
        </div>
        <Badge variant="outline" className={statusClass[runStatus]}>{statusText[runStatus]}</Badge>
      </div>
      <div className="mt-4 space-y-2">
        {steps.map((step) => (
          <PlanStepItem key={step.id} step={step} />
        ))}
      </div>
    </div>
  )
}

function PlanStepItem({ step }: { step: PlanStep }) {
  const Icon = step.status === 'completed' ? CheckCircle2 : step.status === 'running' ? Loader2 : step.status === 'failed' ? XCircle : Clock3
  return (
    <div className="flex items-start gap-3 rounded-xl bg-white px-3 py-2">
      <Icon className={`mt-0.5 h-4 w-4 ${step.status === 'running' ? 'animate-spin text-blue-600' : stepStatusClass(step.status)}`} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-semibold">{step.title}</p>
          {step.toolName && <span className="truncate font-mono text-[11px] text-muted-foreground">{step.toolName}</span>}
        </div>
        {step.description && <p className="mt-0.5 text-xs text-muted-foreground">{step.description}</p>}
      </div>
    </div>
  )
}

function ToolCallCard({ toolCall }: { toolCall: ToolCall }) {
  return (
    <div className="rounded-2xl border border-border bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span className={`rounded-lg p-2 ${toolTone(toolCall.action)}`}>
            <Wand2 className="h-4 w-4" />
          </span>
          <div className="min-w-0">
            <p className="truncate font-mono text-sm font-bold">{toolCall.tool}.{toolCall.action}</p>
            <p className="mt-1 text-xs text-muted-foreground">{toolCall.summary || '等待工具返回结构化结果'}</p>
          </div>
        </div>
        <ToolStatusBadge status={toolCall.status} />
      </div>
      <details className="mt-3 rounded-xl bg-[#f7f8fa] px-3 py-2">
        <summary className="cursor-pointer text-xs font-semibold text-muted-foreground">查看输入 payload</summary>
        <pre className="mt-2 max-h-40 overflow-auto text-xs leading-5">{JSON.stringify(toolCall.payload, null, 2)}</pre>
      </details>
    </div>
  )
}

function ApprovalRequestCard({
  approval,
  onApprove,
  onReject,
}: {
  approval: ApprovalRequest
  onApprove: (id: string) => void
  onReject: (id: string) => void
}) {
  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-950">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
        <div className="min-w-0 flex-1">
          <h3 className="font-bold">需要确认后继续</h3>
          <p className="mt-1 text-sm">{approval.reason || `是否确认执行 ${approval.action}？`}</p>
          <ul className="mt-3 space-y-1 text-xs">
            <li>影响：可能生成或覆盖分析产物</li>
            <li>风险：{approval.riskLevel.toUpperCase()}，执行前会保留审计记录</li>
          </ul>
        </div>
        <div className="flex shrink-0 gap-2">
          <Button size="sm" variant="outline" className="bg-white" onClick={() => onReject(approval.id)}>
            <X className="mr-1 h-4 w-4" />
            拒绝
          </Button>
          <Button size="sm" onClick={() => onApprove(approval.id)}>
            <Check className="mr-1 h-4 w-4" />
            确认
          </Button>
        </div>
      </div>
    </div>
  )
}

function ArtifactPreviewCard({ artifact }: { artifact: ArtifactPreview }) {
  return (
    <div className="rounded-2xl border border-border bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="rounded-lg bg-blue-50 p-2 text-blue-600">
            <FileBarChart className="h-4 w-4" />
          </span>
          <div>
            <h3 className="text-sm font-bold">{artifact.name}</h3>
            <p className="mt-1 text-xs text-muted-foreground">{artifact.path || '已注册到项目 artifact 表'}</p>
          </div>
        </div>
        <Badge variant="outline">{artifact.type}</Badge>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
        {['GMV +61.2%', '曝光 75.9%', '加码 4 类'].map((metric) => (
          <div key={metric} className="rounded-lg bg-[#f7f8fa] px-2 py-2 font-semibold">{metric}</div>
        ))}
      </div>
    </div>
  )
}

function AgentMessageComposer({
  value,
  disabled,
  isRunning,
  onChange,
  onSend,
}: {
  value: string
  disabled: boolean
  isRunning: boolean
  onChange: (value: string) => void
  onSend: () => void
}) {
  return (
    <div className="agent-composer shrink-0 border-t border-border">
      <div className="agent-composer-box rounded-2xl border border-border bg-white shadow-sm focus-within:border-[#f2cf4a]">
        <div className="flex gap-3">
          <button className="mt-1 rounded-lg p-2 text-muted-foreground hover:bg-[#f7f8fa]" aria-label="添加附件" type="button">
            <Paperclip className="h-4 w-4" />
          </button>
          <textarea
            value={value}
            disabled={disabled}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                onSend()
              }
            }}
            className="agent-composer-input flex-1 resize-none border-0 bg-transparent px-0 text-sm outline-none placeholder:text-muted-foreground disabled:opacity-60"
            placeholder="请输入您的问题，例如：分析活动效果、资源配置建议等..."
          />
          <Button className="mt-auto h-10 w-10 rounded-xl p-0" onClick={onSend} disabled={!value.trim() || disabled}>
            {isRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
        <div className="mt-1 flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted-foreground">
          <span>支持 /run、/explain、/report；Enter 发送，Shift + Enter 换行</span>
          <span>消息统一进入 MessageRuntime</span>
        </div>
      </div>
    </div>
  )
}

function AgentSideInspector({
  projectName,
  projectStatus,
  projectStage,
  fileCount,
  artifactCount,
  sessionProvider,
  runStatus,
  activeJob,
  toolCalls,
  planSteps,
  artifacts,
  sessions,
  currentSessionId,
  loadingSessions,
  deletingSessionId,
  onNewThread,
  onContinueSession,
  onDeleteSession,
  lastCompletedAt,
  dashboardHref,
  reportHref,
}: {
  projectName: string
  projectStatus: string
  projectStage: string
  fileCount: number
  artifactCount: number
  sessionProvider: string
  runStatus: AgentRunStatus
  activeJob: JobStatus | null
  toolCalls: ToolCall[]
  planSteps: PlanStep[]
  artifacts: ArtifactPreview[]
  sessions: AgentSession[]
  currentSessionId: string | null
  loadingSessions: boolean
  deletingSessionId: string | null
  onNewThread: () => void
  onContinueSession: (sessionId: string) => void
  onDeleteSession: (sessionId: string) => void
  lastCompletedAt: string | null
  dashboardHref: string
  reportHref: string
}) {
  const progress = Math.round((activeJob?.progress ?? (runStatus === 'completed' ? 1 : runStatus === 'idle' ? 0 : 0.62)) * 100)
  return (
    <aside className="agent-side-inspector flex h-full min-h-0 flex-col overflow-hidden">
      <AgentThreadCard
        sessions={sessions}
        currentSessionId={currentSessionId}
        loading={loadingSessions}
        deletingSessionId={deletingSessionId}
        onNewThread={onNewThread}
        onContinueSession={onContinueSession}
        onDeleteSession={onDeleteSession}
      />

      <InspectorCard title="项目上下文">
        <InfoRow label="项目名称" value={projectName} />
        <InfoRow label="数据周期" value="2025-09-01 ~ 2025-11-30" optional />
        <InfoRow label="活动窗口" value="4 个（33 天）" optional />
        <InfoRow label="品类数量" value="366" optional />
        <InfoRow label="当前状态" value={`${projectStatus} · ${projectStage}`} />
        <InfoRow label="接入文件" value={`${fileCount} 个`} />
      </InspectorCard>

      <InspectorCard title="当前 Run 状态">
        <div className="flex items-center justify-between">
          <Badge variant="outline" className={statusClass[runStatus]}>{statusText[runStatus]}</Badge>
          <span className="agent-hide-when-minimum text-xs text-muted-foreground">{sessionProvider}</span>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-[#eef2f7]">
          <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${progress}%` }} />
        </div>
        <p className="agent-hide-when-minimum mt-2 text-xs font-semibold">{activeJob?.message || '等待下一次分析指令'}</p>
        <div className="mt-2 grid grid-cols-2 gap-1.5 text-xs text-muted-foreground">
          <InfoPill icon={<Timer className="h-3.5 w-3.5" />} label="耗时" value={activeJob ? `${Math.max(1, Math.round(progress / 8))} min` : '-'} />
          <InfoPill icon={<Clock3 className="h-3.5 w-3.5" />} label="完成" value={lastCompletedAt ? formatTime(lastCompletedAt) : '-'} />
        </div>
      </InspectorCard>

      <InspectorCard title="分析进度">
        <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
          {planSteps.map((step) => (
            <div key={step.id} className="flex items-start gap-2">
              <span className={`mt-1 h-2 w-2 rounded-full ${step.status === 'completed' ? 'bg-green-500' : step.status === 'running' ? 'bg-blue-500' : 'bg-gray-300'}`} />
              <div>
                <p className="text-xs font-semibold leading-4">{step.title}</p>
              </div>
            </div>
          ))}
        </div>
      </InspectorCard>

      <InspectorCard title="结果快照">
        <div className="grid grid-cols-4 gap-1.5">
          <MiniKpi label="GMV 净增量" value="+1,290 万" tone="green" />
          <MiniKpi label="曝光贡献" value="+980 万" tone="blue" />
          <MiniKpi label="折扣贡献" value="+180 万" tone="orange" />
          <MiniKpi label="建议加码" value="4 个品类" tone="purple" />
        </div>
        <Link href={dashboardHref} className="agent-result-link mt-2 flex items-center justify-center gap-2 rounded-lg bg-primary text-xs font-bold text-primary-foreground">
          查看结果看板
          <ArrowRight className="h-4 w-4" />
        </Link>
      </InspectorCard>

      <InspectorCard title="产物与下一步">
        <div className="space-y-1.5">
          <InfoRow label="工具调用" value={`${toolCalls.length} 次`} />
          <InfoRow label="已生成产物" value={`${Math.max(artifactCount, artifacts.length)} 个`} />
          {artifacts.slice(0, 2).map((artifact) => (
            <div key={artifact.id} className="agent-artifact-row rounded-lg border bg-[#fbfcfe] text-xs leading-4">
              <p className="truncate font-semibold">{artifact.name}</p>
              <p className="mt-1 truncate text-muted-foreground">{artifact.path || artifact.id}</p>
            </div>
          ))}
        </div>
        <div className="mt-2 grid grid-cols-3 gap-1.5">
          <Link className="agent-side-action truncate rounded-lg border border-border text-center text-xs font-semibold hover:bg-[#f7f8fa]" href={reportHref}>生成报告</Link>
          <button className="agent-side-action truncate rounded-lg border border-border text-xs font-semibold hover:bg-[#f7f8fa]">解释 DID</button>
          <button className="agent-side-action truncate rounded-lg border border-border text-xs font-semibold hover:bg-[#f7f8fa]">资源复盘</button>
        </div>
      </InspectorCard>
    </aside>
  )
}

function AgentThreadCard({
  sessions,
  currentSessionId,
  loading,
  deletingSessionId,
  onNewThread,
  onContinueSession,
  onDeleteSession,
}: {
  sessions: AgentSession[]
  currentSessionId: string | null
  loading: boolean
  deletingSessionId: string | null
  onNewThread: () => void
  onContinueSession: (sessionId: string) => void
  onDeleteSession: (sessionId: string) => void
}) {
  const visibleSessions = sessions.slice(0, 6)

  return (
    <InspectorCard title="对话线程">
      <div className="mb-2 flex items-center justify-between gap-2">
        <Button variant="outline" size="sm" className="h-8 px-2 text-xs" onClick={onNewThread}>
          <MessageSquarePlus className="mr-1.5 h-3.5 w-3.5" />
          新线程
        </Button>
        <Badge variant="outline" className="border-gray-200 bg-gray-50 text-gray-600">
          {sessions.length} 条
        </Badge>
      </div>
      <div className="max-h-48 space-y-1.5 overflow-y-auto pr-1">
        {loading ? (
          <div className="flex items-center gap-2 rounded-lg bg-[#f7f8fa] px-3 py-2 text-xs text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            正在加载线程
          </div>
        ) : visibleSessions.length === 0 ? (
          <div className="rounded-lg bg-[#f7f8fa] px-3 py-2 text-xs text-muted-foreground">
            发送第一条消息后会生成线程
          </div>
        ) : (
          visibleSessions.map((session) => {
            const isCurrent = session.id === currentSessionId
            const preview = session.last_message || '空线程'
            const deleting = deletingSessionId === session.id
            return (
              <div
                key={session.id}
                className={`flex items-center gap-1.5 rounded-lg border px-2 py-2 ${
                  isCurrent ? 'border-primary/40 bg-primary/10' : 'border-border bg-[#fbfcfe]'
                }`}
              >
                <button
                  type="button"
                  className="flex min-w-0 flex-1 items-start gap-2 text-left"
                  onClick={() => onContinueSession(session.id)}
                  aria-current={isCurrent ? 'true' : undefined}
                >
                  <MessageSquare className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${isCurrent ? 'text-primary' : 'text-muted-foreground'}`} />
                  <span className="min-w-0">
                    <span className="block truncate text-xs font-semibold">
                      {isCurrent ? '当前线程' : `线程 ${session.id.slice(0, 6)}`}
                    </span>
                    <span className="mt-0.5 block truncate text-[11px] leading-4 text-muted-foreground">{preview}</span>
                    <span className="mt-0.5 block text-[10px] leading-4 text-muted-foreground">
                      {session.message_count || 0} 条 · {formatThreadTime(session.last_activity_at || session.updated_at || session.created_at)}
                    </span>
                  </span>
                </button>
                <button
                  type="button"
                  className="rounded-md p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive disabled:opacity-50"
                  onClick={() => onDeleteSession(session.id)}
                  disabled={deleting}
                  aria-label="删除线程"
                  title="删除线程"
                >
                  {deleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                </button>
              </div>
            )
          })
        )}
      </div>
    </InspectorCard>
  )
}

function InspectorCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="agent-inspector-card rounded-xl border border-border bg-white shadow-[var(--shadow-soft)]">
      <h2 className="mb-1 text-sm font-bold leading-5">{title}</h2>
      {children}
    </section>
  )
}

function InfoRow({ label, value, optional = false }: { label: string; value: string; optional?: boolean }) {
  return (
    <div className={`agent-info-row flex items-center justify-between gap-3 border-b border-border last:border-b-0 ${optional ? 'agent-hide-when-minimum' : ''}`}>
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="truncate text-right text-xs font-semibold">{value}</span>
    </div>
  )
}

function InfoPill({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="agent-info-pill rounded-lg bg-[#f7f8fa]">
      <div className="flex items-center gap-1">
        {icon}
        <span>{label}</span>
      </div>
      <p className="font-semibold text-[#1f2937]">{value}</p>
    </div>
  )
}

function MiniKpi({ label, value, tone }: { label: string; value: string; tone: 'green' | 'blue' | 'orange' | 'purple' }) {
  const colors = {
    green: 'bg-green-50 text-green-700',
    blue: 'bg-blue-50 text-blue-700',
    orange: 'bg-orange-50 text-orange-700',
    purple: 'bg-purple-50 text-purple-700',
  }
  return (
    <div className={`agent-mini-kpi rounded-lg ${colors[tone]}`}>
      <p className="truncate text-[10px] font-semibold opacity-80">{label}</p>
      <p className="truncate text-xs font-bold">{value}</p>
    </div>
  )
}

function Avatar({ tone, icon, label }: { tone: 'agent' | 'user'; icon?: ReactNode; label?: string }) {
  return (
    <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-bold ${tone === 'agent' ? 'bg-[#e8f0ff] text-blue-700' : 'bg-primary text-primary-foreground'}`}>
      {icon || label}
    </span>
  )
}

function IconAction({ label, icon }: { label: string; icon: ReactNode }) {
  return (
    <button type="button" className="rounded-md p-1 hover:bg-[#f7f8fa]" aria-label={label} title={label}>
      {icon}
    </button>
  )
}

function ToolStatusBadge({ status }: { status: ToolCall['status'] }) {
  const config: Record<ToolCall['status'], string> = {
    pending: 'border-gray-200 bg-gray-50 text-gray-700',
    running: 'border-blue-200 bg-blue-50 text-blue-700',
    waiting_approval: 'border-amber-200 bg-amber-50 text-amber-800',
    success: 'border-green-200 bg-green-50 text-green-700',
    error: 'border-red-200 bg-red-50 text-red-700',
  }
  const labels: Record<ToolCall['status'], string> = {
    pending: '等待',
    running: '运行中',
    waiting_approval: '待确认',
    success: '完成',
    error: '失败',
  }
  return <Badge variant="outline" className={config[status]}>{labels[status]}</Badge>
}

function stepStatusClass(status: PlanStepStatus) {
  const classes: Record<PlanStepStatus, string> = {
    pending: 'text-gray-400',
    running: 'text-blue-600',
    completed: 'text-green-600',
    failed: 'text-red-600',
  }
  return classes[status]
}

function toolTone(action: string) {
  if (action.includes('validate') || action.includes('get')) return 'bg-blue-50 text-blue-600'
  if (action.includes('recommend')) return 'bg-purple-50 text-purple-600'
  if (action.includes('apply')) return 'bg-yellow-50 text-yellow-700'
  if (action.includes('run')) return 'bg-green-50 text-green-600'
  if (action.includes('report')) return 'bg-orange-50 text-orange-600'
  return 'bg-cyan-50 text-cyan-600'
}

function formatTime(value?: string | null) {
  if (!value) return '-'
  return new Date(value).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function formatThreadTime(value?: string | null) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
