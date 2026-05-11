'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import { Brain, Check, RefreshCw, Sparkles, X } from 'lucide-react'
import { api } from '@/lib/api-client'
import type { MemoryCandidate, ProjectMemory } from '@/lib/api-types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { MarkdownView } from '@/components/markdown-view'
import { isKeemartPromoProject } from '@/features/demo/keemart-demo-data'
import { KeemartDemoMemoryPage } from '@/features/demo/keemart-demo-memory-page'

export default function MemoryPage() {
  const params = useParams<{ project_id: string }>()
  const projectId = params.project_id

  if (isKeemartPromoProject(projectId)) {
    return <KeemartDemoMemoryPage />
  }

  return <ApiBackedMemoryPage projectId={projectId} />
}

function ApiBackedMemoryPage({ projectId }: { projectId: string }) {
  const [candidates, setCandidates] = useState<MemoryCandidate[]>([])
  const [memory, setMemory] = useState<ProjectMemory[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadMemory = useCallback(async () => {
    setLoading(true)
    setError(null)
    const [candidateResponse, memoryResponse] = await Promise.all([
      api.listMemoryCandidates(projectId),
      api.getProjectMemory(projectId),
    ])
    setLoading(false)
    if (!candidateResponse.ok || !candidateResponse.data) {
      setError(candidateResponse.error || '无法加载记忆候选。')
      return
    }
    setCandidates(candidateResponse.data)
    setMemory(memoryResponse.ok && memoryResponse.data ? memoryResponse.data : [])
  }, [projectId])

  async function generateSummary() {
    setBusy(true)
    setError(null)
    const response = await api.generateMemorySummary(projectId)
    setBusy(false)
    if (!response.ok) {
      setError(response.error || '无法生成记忆摘要。')
      return
    }
    await loadMemory()
  }

  async function approve(candidateId: string) {
    setBusy(true)
    const response = await api.approveMemoryCandidate(candidateId)
    setBusy(false)
    if (!response.ok) {
      setError(response.error || '无法通过记忆候选。')
      return
    }
    await loadMemory()
  }

  async function reject(candidateId: string) {
    setBusy(true)
    const response = await api.rejectMemoryCandidate(candidateId)
    setBusy(false)
    if (!response.ok) {
      setError(response.error || '无法拒绝记忆候选。')
      return
    }
    await loadMemory()
  }

  useEffect(() => {
    const timeout = setTimeout(() => {
      void loadMemory()
    }, 0)
    return () => clearTimeout(timeout)
  }, [loadMemory])

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
          <h1 className="text-2xl font-semibold">记忆审核</h1>
          <p className="text-sm text-muted-foreground">在写入项目前审核候选记忆内容。</p>
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={loadMemory} disabled={loading || busy}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button type="button" onClick={generateSummary} disabled={loading || busy}>
            <Sparkles className="mr-2 h-4 w-4" />
            生成摘要
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <Metric title="待审核" value={pending.length} />
        <Metric title="已处理" value={reviewed.length} />
        <Metric title="已存储" value={storedMemory ? 1 : 0} />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">候选记忆</CardTitle>
          </CardHeader>
          <CardContent>
            {loading && <p className="text-sm text-muted-foreground">正在加载候选记忆...</p>}
            {!loading && candidates.length === 0 && (
              <p className="text-sm text-muted-foreground">暂无记忆候选。</p>
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
                  <div className="max-h-56 overflow-auto rounded bg-secondary/40 p-3">
                    <MarkdownView content={candidate.content} compact />
                  </div>
                  {candidate.status === 'pending' && (
                    <div className="mt-3 flex justify-end gap-2">
                      <Button type="button" size="sm" variant="outline" onClick={() => reject(candidate.id)} disabled={busy}>
                        <X className="mr-1 h-3.5 w-3.5" />
                        拒绝
                      </Button>
                      <Button type="button" size="sm" onClick={() => approve(candidate.id)} disabled={busy}>
                        <Check className="mr-1 h-3.5 w-3.5" />
                        通过
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
            <CardTitle className="text-base">已存储的项目记忆</CardTitle>
          </CardHeader>
          <CardContent>
            {storedMemory ? (
              <div className="max-h-[65vh] overflow-auto rounded bg-secondary/40 p-3">
                <MarkdownView content={storedMemory} compact />
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">暂无已通过并写入的项目记忆。</p>
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
