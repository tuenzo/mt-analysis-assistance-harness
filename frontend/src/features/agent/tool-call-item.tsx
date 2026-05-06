'use client'

import type { ToolCall } from '@/store/agent-store'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { ChevronDown, ChevronRight, Loader2, CheckCircle, XCircle, Clock, ShieldCheck } from 'lucide-react'
import { useState } from 'react'

interface ToolCallItemProps {
  toolCall: ToolCall
  onSelect?: (toolCall: ToolCall) => void
  isSelected?: boolean
}

const statusConfig = {
  pending: { color: 'secondary', icon: Clock, label: 'Pending' },
  running: { color: 'default', icon: Loader2, label: 'Running' },
  waiting_approval: { color: 'secondary', icon: ShieldCheck, label: 'Approval' },
  success: { color: 'default', icon: CheckCircle, label: 'Success' },
  error: { color: 'destructive', icon: XCircle, label: 'Error' },
}

export function ToolCallItem({ toolCall, onSelect, isSelected }: ToolCallItemProps) {
  const [expanded, setExpanded] = useState(false)

  const status = statusConfig[toolCall.status]
  const StatusIcon = status.icon

  const isRunning = toolCall.status === 'running'

  return (
    <Card
      className={`cursor-pointer transition-colors ${
        isSelected ? 'border-primary' : ''
      } ${isRunning ? 'animate-pulse' : ''}`}
      onClick={() => onSelect?.(toolCall)}
    >
      <CardHeader className="p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={(e) => {
                e.stopPropagation()
                setExpanded(!expanded)
              }}
              className="p-1 hover:bg-accent rounded"
            >
              {expanded ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronRight className="h-3 w-3" />
              )}
            </button>
            <span className="font-mono text-sm font-medium">
              {toolCall.tool}.{toolCall.action}
            </span>
          </div>
          <Badge variant={status.color as 'default' | 'secondary' | 'destructive'}>
            <StatusIcon className={`h-3 w-3 mr-1 ${isRunning ? 'animate-spin' : ''}`} />
            {status.label}
          </Badge>
        </div>
      </CardHeader>

      {expanded && (
        <CardContent className="p-3 pt-0 space-y-3">
          <div>
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
              Payload
            </h4>
            <pre className="bg-muted p-2 rounded text-xs overflow-auto max-h-40">
              {JSON.stringify(toolCall.payload, null, 2)}
            </pre>
          </div>

          {toolCall.summary && (
            <div>
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
                Result Summary
              </h4>
              <p className="text-sm bg-muted p-2 rounded">{toolCall.summary}</p>
            </div>
          )}

          <div className="flex gap-4 text-xs text-muted-foreground">
            {toolCall.startedAt && (
              <span>Started: {new Date(toolCall.startedAt).toLocaleTimeString()}</span>
            )}
            {toolCall.finishedAt && (
              <span>Finished: {new Date(toolCall.finishedAt).toLocaleTimeString()}</span>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  )
}
