import { create } from 'zustand'
import type { AgentSession, AgentMessage, MessageResponse, SSEEvent } from '@/lib/api-types'
import { api } from '@/lib/api-client'

// Extended types for Agent Command Center
export interface ToolCall {
  id: string
  turnId: string
  tool: string
  action: string
  payload: Record<string, unknown>
  status: 'pending' | 'running' | 'success' | 'error'
  result?: Record<string, unknown>
  summary?: string
  startedAt?: string
  finishedAt?: string
}

export interface ApprovalRequest {
  id: string
  turnId: string
  action: string
  reason: string
  riskLevel: 'low' | 'medium' | 'high'
  payload: Record<string, unknown>
  createdAt: string
}

export interface JobStatus {
  id: string
  turnId: string
  action: string
  currentStep: string
  totalSteps: number
  progress: number
  message: string
}

interface AgentStore {
  // Existing state
  sessions: Record<string, AgentSession>
  currentSession: AgentSession | null
  messageQueue: AgentMessage[]
  isRunning: boolean
  error: string | null

  // New state for Agent Command Center
  toolCalls: Record<string, ToolCall[]> // turnId -> toolCalls
  approvalRequests: ApprovalRequest[]
  jobs: Record<string, JobStatus> // jobId -> JobStatus
  selectedToolCall: ToolCall | null

  // Actions
  createSession: (projectId: string) => Promise<string | null>
  setCurrentSession: (sessionId: string | null) => void
  sendMessage: (projectId: string, message: string) => Promise<MessageResponse | null>
  loadSessionMessages: (sessionId: string) => Promise<void>
  handleSSEEvent: (event: SSEEvent) => void
  interruptSession: (sessionId: string) => Promise<void>
  clearMessages: () => void
  clearError: () => void
  failRun: (error: string) => void
  selectToolCall: (toolCall: ToolCall | null) => void
  approveApproval: (approvalId: string) => Promise<void>
  rejectApproval: (approvalId: string) => Promise<void>
}

export const useAgentStore = create<AgentStore>((set, get) => ({
  sessions: {},
  currentSession: null,
  messageQueue: [],
  isRunning: false,
  error: null,

  toolCalls: {},
  approvalRequests: [],
  jobs: {},
  selectedToolCall: null,

  createSession: async (projectId: string) => {
    void projectId
    return null
  },

  setCurrentSession: (sessionId: string | null) => {
    if (!sessionId) {
      set({ currentSession: null })
      return
    }

    const session = get().sessions[sessionId]
    if (session) {
      set({ currentSession: session })
    }
  },

  sendMessage: async (projectId: string, message: string) => {
    set({ isRunning: true, error: null })

    try {
      const sessionId = get().currentSession?.id
      const response = await api.createMessage(projectId, message, sessionId || undefined)

      if (response.ok && response.data) {
        const { session_id, turn_id } = response.data

        // Update or create session
        if (!get().sessions[session_id]) {
          const sessionResponse = await api.getSession(session_id)
          if (sessionResponse.ok && sessionResponse.data) {
            const sessionData = sessionResponse.data as AgentSession
            set((state) => ({
              ...state,
              sessions: {
                ...state.sessions,
                [session_id]: sessionData,
              },
              currentSession: sessionData,
            }))
          }
        }

        // Add user message to queue
        const userMessage: AgentMessage = {
          id: `msg_${Date.now()}_user`,
          turn_id,
          role: 'user',
          content: message,
          created_at: new Date().toISOString(),
        }

        set((state) => ({
          messageQueue: [...state.messageQueue, userMessage],
        }))

        return response.data
      } else {
        set({ error: response.error || 'Failed to send message', isRunning: false })
        return null
      }
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Unknown error', isRunning: false })
      return null
    }
  },

  loadSessionMessages: async (sessionId: string) => {
    try {
      const [sessionResponse, messagesResponse] = await Promise.all([
        api.getSession(sessionId),
        api.getSessionMessages(sessionId),
      ])
      if (sessionResponse.ok && sessionResponse.data) {
        const sessionData = sessionResponse.data as AgentSession
        set((state) => ({
          sessions: {
            ...state.sessions,
            [sessionId]: sessionData,
          },
          currentSession: sessionData,
        }))
      }
      if (messagesResponse.ok && messagesResponse.data) {
        set({ messageQueue: messagesResponse.data })
      }
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to load session history' })
    }
  },

  handleSSEEvent: (event: SSEEvent) => {
    switch (event.type) {
      case 'assistant_message_delta':
        set((state) => {
          const messages = [...state.messageQueue]
          const lastMsg = messages[messages.length - 1]
          if (lastMsg && lastMsg.role === 'assistant') {
            lastMsg.content += event.delta
          } else {
            messages.push({
              id: `msg_${Date.now()}_assistant`,
              turn_id: event.turn_id,
              role: 'assistant',
              content: event.delta,
              created_at: new Date().toISOString(),
            })
          }
          return { messageQueue: messages }
        })
        break

      case 'tool_call_started':
        {
          const toolCall: ToolCall = {
            id: `tc_${Date.now()}`,
            turnId: event.turn_id,
            tool: event.tool,
            action: event.action,
            payload: event.payload || {},
            status: 'running',
            startedAt: new Date().toISOString(),
          }

          set((state) => {
            const turnToolCalls = state.toolCalls[event.turn_id] || []
            return {
              toolCalls: {
                ...state.toolCalls,
                [event.turn_id]: [...turnToolCalls, toolCall],
              },
            }
          })
        }
        break

      case 'tool_call_finished':
        {
          const toolName = event.tool
          const actionName = event.action

          set((state) => {
            const updatedToolCalls: Record<string, ToolCall[]> = {}
            for (const [turnId, calls] of Object.entries(state.toolCalls)) {
              updatedToolCalls[turnId] = calls.map((tc) => {
                if (tc.tool === toolName && tc.action === actionName && tc.status === 'running') {
                  return {
                    ...tc,
                    status: event.ok ? 'success' : 'error',
                    summary: event.summary,
                    finishedAt: new Date().toISOString(),
                  }
                }
                return tc
              })
            }
            return { toolCalls: updatedToolCalls }
          })
        }
        break

      case 'tool_call_failed':
        {
          const toolName = event.tool
          const actionName = event.action

          set((state) => {
            const updatedToolCalls: Record<string, ToolCall[]> = {}
            for (const [turnId, calls] of Object.entries(state.toolCalls)) {
              updatedToolCalls[turnId] = calls.map((tc) => {
                if (tc.tool === toolName && tc.action === actionName && tc.status === 'running') {
                  return {
                    ...tc,
                    status: 'error',
                    summary: event.error || 'Tool call failed',
                    finishedAt: new Date().toISOString(),
                  }
                }
                return tc
              })
            }
            return { toolCalls: updatedToolCalls }
          })
        }
        break

      case 'job_started':
        {
          const job: JobStatus = {
            id: event.job_id,
            turnId: event.turn_id,
            action: event.action,
            currentStep: '',
            totalSteps: 8,
            progress: 0,
            message: 'Starting...',
          }
          set((state) => ({
            jobs: {
              ...state.jobs,
              [event.job_id]: job,
            },
          }))
        }
        break

      case 'job_progress':
        {
          const currentJob = get().jobs[event.job_id]
          const totalSteps = currentJob?.totalSteps || 8
          const job: JobStatus = {
            id: event.job_id,
            turnId: event.turn_id,
            action: currentJob?.action || '',
            currentStep: `Step ${Math.floor(event.progress * totalSteps)}`,
            totalSteps,
            progress: event.progress,
            message: event.message,
          }
          set((state) => ({
            jobs: {
              ...state.jobs,
              [event.job_id]: job,
            },
          }))
        }
        break

      case 'job_finished':
        {
          set((state) => {
            const rest = { ...state.jobs }
            delete rest[event.job_id]
            return { jobs: rest }
          })
        }
        break

      case 'approval_requested':
        {
          const approval: ApprovalRequest = {
            id: event.approval_id,
            turnId: event.turn_id,
            action: event.action,
            reason: event.reason,
            riskLevel: 'medium', // Default, actual risk level would come from backend
            payload: {},
            createdAt: new Date().toISOString(),
          }
          set((state) => ({
            approvalRequests: [...state.approvalRequests, approval],
          }))
        }
        break

      case 'final_answer':
        set((state) => {
          const messages = [...state.messageQueue]
          const lastMsg = messages[messages.length - 1]
          if (lastMsg && lastMsg.role === 'assistant') {
            // Update existing assistant message with the final content
            lastMsg.content = event.message
          } else {
            // No assistant message yet, append one
            messages.push({
              id: `msg_${Date.now()}_final`,
              turn_id: event.turn_id,
              role: 'assistant',
              content: event.message,
              created_at: new Date().toISOString(),
            })
          }
          return { messageQueue: messages, isRunning: false }
        })
        break

      case 'error':
        set({ error: event.error, isRunning: false })
        break

      case 'runtime_error':
        set({ error: event.error, isRunning: false })
        break

      case 'session_created':
        if (event.session_id) {
          api.getSession(event.session_id).then((response) => {
            if (response.ok && response.data) {
              set((state) => ({
                sessions: {
                  ...state.sessions,
                  [event.session_id!]: response.data as AgentSession,
                },
                currentSession: response.data as AgentSession,
              }))
            }
          })
        }
        break
    }
  },

  interruptSession: async (sessionId: string) => {
    try {
      await api.interruptSession(sessionId)
      set({ isRunning: false })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to interrupt session' })
    }
  },

  clearMessages: () => set({ messageQueue: [], toolCalls: {}, approvalRequests: [], jobs: {} }),

  clearError: () => set({ error: null }),

  failRun: (error: string) => set({ error, isRunning: false }),

  selectToolCall: (toolCall: ToolCall | null) => set({ selectedToolCall: toolCall }),

  approveApproval: async (approvalId: string) => {
    try {
      await api.approveApproval(approvalId)
      set((state) => ({
        approvalRequests: state.approvalRequests.filter((a) => a.id !== approvalId),
      }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to approve' })
    }
  },

  rejectApproval: async (approvalId: string) => {
    try {
      await api.rejectApproval(approvalId)
      set((state) => ({
        approvalRequests: state.approvalRequests.filter((a) => a.id !== approvalId),
      }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to reject' })
    }
  },
}))
