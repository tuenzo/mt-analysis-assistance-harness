'use client'

const HANDOFF_STORAGE_PREFIX = 'business-analysis-agent-handoff:'

export type AgentHandoffPayload = {
  id: string
  projectId: string
  source: 'dashboard-drilldown'
  title: string
  context: string
  suggestedQuestion: string
  createdAt: string
}

export function createAgentHandoff(payload: Omit<AgentHandoffPayload, 'id' | 'createdAt'>): string | null {
  if (typeof window === 'undefined') return null

  const id = `handoff_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  const fullPayload: AgentHandoffPayload = {
    ...payload,
    id,
    createdAt: new Date().toISOString(),
  }

  try {
    window.sessionStorage.setItem(storageKey(id), JSON.stringify(fullPayload))
    return id
  } catch {
    return null
  }
}

export function readAgentHandoff(id: string | null): AgentHandoffPayload | null {
  if (!id || typeof window === 'undefined') return null

  try {
    const raw = window.sessionStorage.getItem(storageKey(id))
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<AgentHandoffPayload>
    if (!parsed.id || !parsed.projectId || !parsed.title || !parsed.context) return null
    return parsed as AgentHandoffPayload
  } catch {
    return null
  }
}

export function removeAgentHandoff(id: string | null) {
  if (!id || typeof window === 'undefined') return
  try {
    window.sessionStorage.removeItem(storageKey(id))
  } catch {
    // Ignore storage cleanup failures.
  }
}

export function buildAgentHandoffMessage(payload: AgentHandoffPayload) {
  return [
    '请在一个新的分析线程中接收以下看板卡片上下文。',
    '先确认你已经读取上下文，并等待我的后续问题；除非我明确要求，不要重新运行 pipeline 或生成报告。',
    '',
    `项目：${payload.projectId}`,
    `来源：${payload.source}`,
    `卡片：${payload.title}`,
    `创建时间：${payload.createdAt}`,
    '',
    payload.context,
  ].join('\n')
}

function storageKey(id: string) {
  return `${HANDOFF_STORAGE_PREFIX}${id}`
}
