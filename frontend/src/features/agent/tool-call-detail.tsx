'use client'

import type { ToolCall } from '@/store/agent-store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { X, CheckCircle, XCircle, Loader2, Clock, ShieldCheck } from 'lucide-react'

interface ToolCallDetailProps {
  toolCall: ToolCall | null
  onClose?: () => void
}

const statusConfig = {
  pending: { color: 'secondary', icon: Clock, label: 'Pending' },
  running: { color: 'default', icon: Loader2, label: 'Running' },
  waiting_approval: { color: 'secondary', icon: ShieldCheck, label: 'Approval' },
  success: { color: 'default', icon: CheckCircle, label: 'Success' },
  error: { color: 'destructive', icon: XCircle, label: 'Error' },
}

export function ToolCallDetail({ toolCall, onClose }: ToolCallDetailProps) {
  if (!toolCall) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
        Select a tool call to view details
      </div>
    )
  }

  const status = statusConfig[toolCall.status]
  const StatusIcon = status.icon

  return (
    <Card className="h-full border-0 rounded-none">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Tool Call Details</CardTitle>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 hover:bg-accent rounded"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Status</span>
            <Badge variant={status.color as 'default' | 'secondary' | 'destructive'}>
              <StatusIcon className={`h-3 w-3 mr-1 ${toolCall.status === 'running' ? 'animate-spin' : ''}`} />
              {status.label}
            </Badge>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Tool</span>
            <span className="font-mono text-sm">{toolCall.tool}</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Action</span>
            <span className="font-mono text-sm">{toolCall.action}</span>
          </div>
        </div>

        <div>
          <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
            Payload
          </h4>
          <pre className="bg-muted p-3 rounded text-xs overflow-auto max-h-60">
            {JSON.stringify(toolCall.payload, null, 2)}
          </pre>
        </div>

        {toolCall.result && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
              Full Result
            </h4>
            <pre className="bg-muted p-3 rounded text-xs overflow-auto max-h-60">
              {JSON.stringify(toolCall.result, null, 2)}
            </pre>
          </div>
        )}

        {toolCall.summary && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
              Summary
            </h4>
            <p className="text-sm bg-muted p-3 rounded">{toolCall.summary}</p>
          </div>
        )}

        <div className="text-xs text-muted-foreground space-y-1">
          <p>ID: {toolCall.id}</p>
          {toolCall.startedAt && (
            <p>Started: {new Date(toolCall.startedAt).toLocaleString()}</p>
          )}
          {toolCall.finishedAt && (
            <p>Finished: {new Date(toolCall.finishedAt).toLocaleString()}</p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
