'use client'

import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { Toaster, toast } from 'sonner'
import { useAgentStore } from '@/store/agent-store'
import { useAgentEvents } from '@/lib/sse-hooks'
import { api } from '@/lib/api-client'
import type { SSEEvent } from '@/lib/api-types'
import { MessageList } from '@/features/agent/message-list'
import { MessageInput } from '@/features/agent/message-input'
import { ToolCallItem } from '@/features/agent/tool-call-item'
import { ToolCallDetail } from '@/features/agent/tool-call-detail'
import { ApprovalBanner } from '@/features/agent/approval-banner'
import { JobProgressIndicator } from '@/features/agent/job-progress-indicator'
import { Button } from '@/components/ui/button'
import { Bot, Square, Trash2 } from 'lucide-react'

export default function AgentPage() {
  const params = useParams()
  const projectId = params.project_id as string

  const {
    messageQueue,
    isRunning,
    error,
    toolCalls,
    approvalRequests,
    jobs,
    selectedToolCall,
    sendMessage,
    loadSessionMessages,
    loadPendingApprovals,
    handleSSEEvent,
    interruptSession,
    clearMessages,
    failRun,
    selectToolCall,
    approveApproval,
    rejectApproval,
  } = useAgentStore()

  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [turnId, setTurnId] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api.getDemoStatus().then(async (response) => {
      if (
        !cancelled &&
        response.ok &&
        response.data?.enabled &&
        response.data.project_id === projectId &&
        response.data.session_id
      ) {
        setSessionId(response.data.session_id)
        await loadSessionMessages(response.data.session_id)
      }
    })
    return () => {
      cancelled = true
    }
  }, [projectId, loadSessionMessages])

  useEffect(() => {
    if (sessionId) {
      void loadPendingApprovals(projectId, sessionId)
    }
  }, [projectId, sessionId, loadPendingApprovals])

  // Handle SSE events with toast notifications
  const handleEventWithToast = useCallback((event: SSEEvent) => {
    // Show toast for artifact created
    if (event.type === 'artifact_created') {
      toast.success(`Artifact created: ${event.name}`, {
        description: event.path,
        duration: 5000,
      })
    }
    handleSSEEvent(event)
  }, [handleSSEEvent])

  const handleSSEError = useCallback((eventError: Error) => {
    failRun(eventError.message)
  }, [failRun])

  const { connected, error: sseError } = useAgentEvents(sessionId, turnId, {
    onEvent: handleEventWithToast,
    onError: handleSSEError,
  })

  // Get current turn's tool calls
  const currentTurnId = messageQueue.length > 0 ? messageQueue[messageQueue.length - 1].turn_id : null
  const currentToolCalls = currentTurnId ? toolCalls[currentTurnId] || [] : []

  const handleSend = async () => {
    if (!input.trim() || isRunning) return

    const messageResponse = await sendMessage(projectId, input.trim())
    if (messageResponse) {
      setSessionId(messageResponse.session_id)
      setTurnId(messageResponse.turn_id)
    }
    setInput('')
  }

  const handleInterrupt = () => {
    if (sessionId) {
      interruptSession(sessionId)
    }
  }

  // Get the active job
  const activeJob = Object.values(jobs)[0] || null

  return (
    <div className="flex flex-col h-full">
      <Toaster position="top-right" richColors />

      {/* Header */}
      <div className="flex items-center justify-between border-b px-4 py-3 bg-card">
        <div className="flex items-center gap-3">
          <Bot className="h-5 w-5" />
          <span className="font-medium">Agent Command Center</span>
          <span
            className={`text-xs px-2 py-0.5 rounded-full ${
              connected
                ? 'bg-green-100 text-green-700'
                : sseError
                ? 'bg-red-100 text-red-700'
                : 'bg-gray-100 text-gray-700'
            }`}
          >
            {connected ? 'Connected' : sseError ? 'Disconnected' : 'Idle'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {isRunning && sessionId && (
            <Button variant="outline" size="sm" onClick={handleInterrupt}>
              <Square className="h-4 w-4 mr-1" />
              Interrupt
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={clearMessages}>
            <Trash2 className="h-4 w-4 mr-1" />
            Clear
          </Button>
        </div>
      </div>

      {/* Approval Banners */}
      {approvalRequests.length > 0 && (
        <div className="p-4 space-y-2">
          {approvalRequests.map((approval) => (
            <ApprovalBanner
              key={approval.id}
              approval={approval}
              onApprove={approveApproval}
              onReject={rejectApproval}
            />
          ))}
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Message List */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <MessageList messages={messageQueue} isRunning={isRunning} />
          <MessageInput
            value={input}
            onChange={setInput}
            onSend={handleSend}
            onInterrupt={handleInterrupt}
            disabled={!projectId}
            isRunning={isRunning}
          />
        </div>

        {/* Right: Tool Calls Panel */}
        {currentToolCalls.length > 0 && (
          <div className="w-80 border-l bg-card overflow-y-auto">
            <div className="p-4 border-b">
              <h3 className="font-medium text-sm">Tool Calls</h3>
            </div>
            <div className="p-2 space-y-2">
              {currentToolCalls.map((toolCall, index) => (
                <ToolCallItem
                  key={`${toolCall.turnId}_${toolCall.id}_${toolCall.startedAt || index}`}
                  toolCall={toolCall}
                  isSelected={selectedToolCall?.id === toolCall.id}
                  onSelect={selectToolCall}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Tool Call Detail Panel */}
      {selectedToolCall && (
        <div className="border-t">
          <ToolCallDetail
            toolCall={selectedToolCall}
            onClose={() => selectToolCall(null)}
          />
        </div>
      )}

      {/* Job Progress Indicator */}
      {activeJob && (
        <div className="border-t p-4 bg-card">
          <JobProgressIndicator job={activeJob} jobs={jobs} />
        </div>
      )}

      {/* Error Banner */}
      {(error || sseError) && (
        <div className="px-4 py-2 bg-destructive/10 text-destructive text-sm">
          {error || sseError?.message}
        </div>
      )}
    </div>
  )
}
