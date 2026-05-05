'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import { Activity, CheckCircle2, Clock, RefreshCw, ShieldCheck, XCircle } from 'lucide-react'
import { api } from '@/lib/api-client'
import type { ProjectTimeline, TimelineEntry } from '@/lib/api-types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

type TimelineItem = TimelineEntry & { kind: 'job' | 'tool' | 'approval' | 'event'; label: string }

export default function TimelinePage() {
  const params = useParams<{ project_id: string }>()
  const projectId = params.project_id
  const [timeline, setTimeline] = useState<ProjectTimeline | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function loadTimeline() {
    setLoading(true)
    setError(null)
    const response = await api.getProjectTimeline(projectId)
    setLoading(false)
    if (!response.ok || !response.data) {
      setError(response.error || 'Failed to load timeline.')
      return
    }
    setTimeline(response.data)
  }

  useEffect(() => {
    void loadTimeline()
  }, [projectId])

  const items = useMemo(() => flattenTimeline(timeline), [timeline])

  return (
    <div className="container mx-auto max-w-6xl px-4 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Run Timeline</h1>
          <p className="text-sm text-muted-foreground">Jobs, approvals, tool calls, and agent runtime events.</p>
        </div>
        <Button type="button" variant="outline" onClick={loadTimeline} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-4">
        <Metric title="Jobs" value={timeline?.jobs.length ?? 0} />
        <Metric title="Tool Calls" value={timeline?.tool_calls.length ?? 0} />
        <Metric title="Approvals" value={timeline?.approvals.length ?? 0} />
        <Metric title="Events" value={timeline?.events.length ?? 0} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">History</CardTitle>
        </CardHeader>
        <CardContent>
          {loading && <p className="text-sm text-muted-foreground">Loading timeline...</p>}
          {!loading && items.length === 0 && (
            <p className="text-sm text-muted-foreground">No timeline records yet.</p>
          )}
          <div className="space-y-3">
            {items.map((item) => (
              <div key={`${item.kind}_${item.id}`} className="flex gap-3 rounded-md border px-3 py-3">
                <StatusIcon status={item.status || item.type} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-3">
                    <div className="truncate text-sm font-medium">{item.label}</div>
                    <span className="shrink-0 text-xs text-muted-foreground">{formatTime(item.created_at || item.started_at)}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    {item.status && <span className="rounded bg-secondary px-2 py-0.5">{item.status}</span>}
                    {item.progress !== undefined && <span>{Math.round(item.progress * 100)}%</span>}
                    {item.risk_level && <span>{item.risk_level} risk</span>}
                    {item.summary && <span className="truncate">{item.summary}</span>}
                    {item.reason && <span className="truncate">{item.reason}</span>}
                    {item.error_message && <span className="text-destructive">{item.error_message}</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function flattenTimeline(timeline: ProjectTimeline | null): TimelineItem[] {
  if (!timeline) return []
  return [
    ...timeline.jobs.map((item) => ({ ...item, kind: 'job' as const, label: item.action || 'Job' })),
    ...timeline.tool_calls.map((item) => ({ ...item, kind: 'tool' as const, label: item.action || 'Tool call' })),
    ...timeline.approvals.map((item) => ({ ...item, kind: 'approval' as const, label: item.action || 'Approval' })),
    ...timeline.events.map((item) => ({ ...item, kind: 'event' as const, label: item.type || 'Event' })),
  ].sort((a, b) => Date.parse(b.created_at || '') - Date.parse(a.created_at || ''))
}

function Metric({ title, value }: { title: string; value: number }) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-4">
        <div>
          <p className="text-xs text-muted-foreground">{title}</p>
          <p className="mt-1 text-xl font-semibold">{value}</p>
        </div>
        <Clock className="h-5 w-5 text-primary" />
      </CardContent>
    </Card>
  )
}

function StatusIcon({ status }: { status?: string }) {
  if (status === 'succeeded' || status === 'approved' || status === 'job_finished') {
    return <CheckCircle2 className="mt-0.5 h-4 w-4 text-green-600" />
  }
  if (status === 'failed' || status === 'rejected' || status === 'tool_call_failed') {
    return <XCircle className="mt-0.5 h-4 w-4 text-destructive" />
  }
  if (status === 'waiting_approval' || status === 'approval_requested') {
    return <ShieldCheck className="mt-0.5 h-4 w-4 text-amber-600" />
  }
  return <Activity className="mt-0.5 h-4 w-4 text-primary" />
}

function formatTime(value?: string | null) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}
