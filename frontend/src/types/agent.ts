import type { ReactNode } from 'react'

export type AgentRunStatus =
  | 'idle'
  | 'planning'
  | 'waiting_approval'
  | 'running'
  | 'completed'
  | 'failed'

export type PlanStepStatus = 'pending' | 'running' | 'completed' | 'failed'

export type PlanStep = {
  id: string
  title: string
  description?: string
  status: PlanStepStatus
  toolName?: string
}

export type QuickPrompt = {
  label: string
  text: string
  icon?: ReactNode
}

export type ArtifactPreview = {
  id: string
  name: string
  type: string
  path?: string
  metrics?: string[]
}
