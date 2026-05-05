'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import { Brain, Check, RefreshCw, Sparkles, X } from 'lucide-react'
import { api } from '@/lib/api-client'
import type { MemoryCandidate, ProjectMemory } from '@/lib/api-types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function MemoryPage() {
  const params = useParams<{ project_id: string }>()
  const projectId = params.project_id
  const [candidates, setCandidates] = useState<MemoryCandidate[]>([])
  const [memory, setMemory] = useState<ProjectMemory[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function loadMemory() {
    setLoading(true)
    setError(null)
    const [candidateResponse, memoryResponse] = await Promise.all([
      api.listMemoryCandidates(projectId),
      api.getProjectMemory(projectId),
    ])
    setLoading(false)
    if (!candidateResponse.ok || !candidateResponse.data) {
      setError(candidateResponse.error || 'Failed to load memory candidates.')
      return
    }
    setCandidates(candidateResponse.data)
    setMemory(memoryResponse.ok && memoryResponse.data ? memoryResponse.data : [])
  }

  async function generateSummary() {
    setBusy(true)
    setError(null)
    const response = await api.generateMemorySummary(projectId)
    setBusy(false)
    if (!response.ok) {
      setError(response.error || 'Failed to generate memory summary.')
      return
    }
    await loadMemory()
  }

  async function approve(candidateId: string) {
    setBusy(true)
    const response = await api.approveMemoryCandidate(candidateId)
    setBusy(false)
    if (!response.ok) {
      setError(response.error || 'Failed to approve memory candidate.')
      return
    }
    await loadMemory()
  }

  async function reject(candidateId: string) {
    setBusy(true)
    const response = await api.rejectMemoryCandidate(candidateId)
    setBusy(false)
    if (!response.ok) {
      setError(response.error || 'Failed to reject memory candidate.')
      return
    }
    await loadMemory()
  }

  useEffect(() => {
    void loadMemory()
  }, [projectId])

  const pending = candidates.filter((candidate) => candidate.status === 'pending')
  const reviewed = candidates.filter((candidate) => candidate.status !== 'pending')
  const storedMemory = useMemo(
    () => memory.find((item) => item.scope === 'project')?.content || '',
    [memory]
  )

  return (
    <div className="container mx-auto max-w-6xl px-4 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Memory Review</h1>
          <p className="text-sm text-muted-foreground">Review project memory candidates before persistence.</p>
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={loadMemory} disabled={loading || busy}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button type="button" onClick={generateSummary} disabled={loading || busy}>
            <Sparkles className="mr-2 h-4 w-4" />
            Generate
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <Metric title="Pending" value={pending.length} />
        <Metric title="Reviewed" value={reviewed.length} />
        <Metric title="Stored" value={storedMemory ? 1 : 0} />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Candidates</CardTitle>
          </CardHeader>
          <CardContent>
            {loading && <p className="text-sm text-muted-foreground">Loading candidates...</p>}
            {!loading && candidates.length === 0 && (
              <p className="text-sm text-muted-foreground">No memory candidates yet.</p>
            )}
            <div className="space-y-3">
              {candidates.map((candidate) => (
                <div key={candidate.id} className="rounded-md border p-3">
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <Brain className="h-4 w-4 text-primary" />
                      {candidate.scope}
                    </div>
                    <span className="rounded bg-secondary px-2 py-0.5 text-xs text-muted-foreground">
                      {candidate.status}
                    </span>
                  </div>
                  <pre className="max-h-56 overflow-auto whitespace-pre-wrap rounded bg-secondary/40 p-3 text-xs leading-5">
                    {candidate.content}
                  </pre>
                  {candidate.status === 'pending' && (
                    <div className="mt-3 flex justify-end gap-2">
                      <Button type="button" size="sm" variant="outline" onClick={() => reject(candidate.id)} disabled={busy}>
                        <X className="mr-1 h-3.5 w-3.5" />
                        Reject
                      </Button>
                      <Button type="button" size="sm" onClick={() => approve(candidate.id)} disabled={busy}>
                        <Check className="mr-1 h-3.5 w-3.5" />
                        Approve
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Stored Project Memory</CardTitle>
          </CardHeader>
          <CardContent>
            {storedMemory ? (
              <pre className="max-h-[65vh] overflow-auto whitespace-pre-wrap rounded bg-secondary/40 p-3 text-xs leading-5">
                {storedMemory}
              </pre>
            ) : (
              <p className="text-sm text-muted-foreground">No approved project memory has been stored yet.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function Metric({ title, value }: { title: string; value: number }) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-4">
        <div>
          <p className="text-xs text-muted-foreground">{title}</p>
          <p className="mt-1 text-xl font-semibold">{value}</p>
        </div>
        <Brain className="h-5 w-5 text-primary" />
      </CardContent>
    </Card>
  )
}
