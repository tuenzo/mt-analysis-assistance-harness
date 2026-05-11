'use client'

import { useMemo, useState } from 'react'
import { Brain, Check, Clock3, Database, RefreshCw, ShieldCheck, Sparkles, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { MarkdownView } from '@/components/markdown-view'
import {
  keemartMemoryCandidates,
  keemartMemoryReuseRules,
  keemartStoredProjectMemory,
  type KeemartMemoryCandidate,
  type KeemartMemoryCandidateStatus,
} from '@/features/demo/keemart-demo-data'

const statusText: Record<KeemartMemoryCandidateStatus, string> = {
  pending: '待审核',
  approved: '已写入',
  rejected: '已忽略',
}

const statusClassName: Record<KeemartMemoryCandidateStatus, string> = {
  pending: 'bg-[#fff7d6] text-[#7a4d00]',
  approved: 'bg-[#dcfce7] text-[#166534]',
  rejected: 'bg-[#f3f4f6] text-[#6b7280]',
}

export function KeemartDemoMemoryPage() {
  const [candidates, setCandidates] = useState<KeemartMemoryCandidate[]>(keemartMemoryCandidates)
  const [storedMemory, setStoredMemory] = useState(keemartStoredProjectMemory)
  const [notice, setNotice] = useState('已从最新复盘产物生成候选记忆，等待项目内审核。')

  const metrics = useMemo(() => {
    const pending = candidates.filter((candidate) => candidate.status === 'pending').length
    const approved = candidates.filter((candidate) => candidate.status === 'approved').length
    return [
      { title: '待审核', value: pending, helper: '候选记忆需人工确认', icon: Clock3 },
      { title: '已写入', value: approved, helper: '进入项目级上下文', icon: Brain },
      { title: '复用规则', value: keemartMemoryReuseRules.length, helper: '用于下一轮活动', icon: Sparkles },
    ]
  }, [candidates])

  function updateCandidate(candidateId: string, status: KeemartMemoryCandidateStatus) {
    const target = candidates.find((candidate) => candidate.id === candidateId)
    setCandidates((current) =>
      current.map((candidate) =>
        candidate.id === candidateId
          ? {
              ...candidate,
              status,
            }
          : candidate,
      ),
    )

    if (status === 'approved' && target) {
      setStoredMemory((current) => `${current}\n- ${target.title}：${target.content}`)
      setNotice(`已将“${target.title}”写入项目级记忆。`)
      return
    }

    if (status === 'rejected' && target) {
      setNotice(`已忽略“${target.title}”，不会进入项目级记忆。`)
    }
  }

  function resetMemory() {
    setCandidates(keemartMemoryCandidates)
    setStoredMemory(keemartStoredProjectMemory)
    setNotice('已从最新复盘产物生成候选记忆，等待项目内审核。')
  }

  return (
    <div className="container mx-auto max-w-6xl space-y-4 px-4 py-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.12em] text-[#8a6a00]">
            <ShieldCheck className="h-4 w-4" />
            Project Memory Review
          </div>
          <h1 className="mt-1.5 text-2xl font-semibold">记忆审核</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            将本轮促销复盘中的稳定口径、策略规则和风险边界沉淀到项目级记忆。
          </p>
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={resetMemory}>
            <RefreshCw className="mr-2 h-4 w-4" />
            重新生成
          </Button>
          <Button type="button" onClick={() => setNotice('候选记忆已按报告、看板和 Agent 结论重新汇总。')}>
            <Sparkles className="mr-2 h-4 w-4" />
            生成摘要
          </Button>
        </div>
      </div>

      <div className="rounded-xl border border-[#f2cf4a]/60 bg-[#fff9db] px-4 py-2.5 text-sm font-medium text-[#654400]">
        {notice}
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {metrics.map((metric) => {
          const Icon = metric.icon
          return (
            <Card key={metric.title}>
              <CardContent className="flex min-h-[78px] items-center gap-3 p-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-secondary">
                  <Icon className="h-4.5 w-4.5 text-[#d49700]" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-3">
                    <p className="truncate text-sm font-bold text-[#111827]">{metric.title}</p>
                    <p className="text-xl font-black leading-none text-[#111827]">{metric.value}</p>
                  </div>
                  <p className="mt-1 truncate text-xs leading-4 text-muted-foreground">{metric.helper}</p>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <div className="grid gap-3 lg:grid-cols-[1.2fr_0.8fr]">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">候选记忆</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {candidates.map((candidate) => (
              <MemoryCandidateCard
                key={candidate.id}
                candidate={candidate}
                onApprove={() => updateCandidate(candidate.id, 'approved')}
                onReject={() => updateCandidate(candidate.id, 'rejected')}
              />
            ))}
          </CardContent>
        </Card>

        <div className="space-y-3">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <Database className="h-4 w-4 text-[#d49700]" />
                已存储的项目记忆
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="max-h-[420px] overflow-auto rounded-xl bg-[#f7f8fa] p-3">
                <MarkdownView content={storedMemory} compact />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">下一轮复用方式</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2.5">
              {keemartMemoryReuseRules.map((rule, index) => (
                <div key={rule} className="flex gap-3 rounded-xl border border-border bg-white p-2.5 text-sm">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-secondary text-xs font-bold text-[#7a4d00]">
                    {index + 1}
                  </span>
                  <span className="leading-6 text-[#374151]">{rule}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

function MemoryCandidateCard({
  candidate,
  onApprove,
  onReject,
}: {
  candidate: KeemartMemoryCandidate
  onApprove: () => void
  onReject: () => void
}) {
  const reviewed = candidate.status !== 'pending'

  return (
    <div className="rounded-xl border border-border bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-sm font-bold text-[#111827]">{candidate.title}</h2>
            <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${statusClassName[candidate.status]}`}>
              {statusText[candidate.status]}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            来源：{candidate.source} · 置信度：{candidate.confidence} · 范围：{candidate.scope}
          </p>
        </div>
        <div className="flex gap-2">
          <Button type="button" size="sm" variant="outline" onClick={onReject} disabled={reviewed}>
            <X className="mr-1 h-3.5 w-3.5" />
            忽略
          </Button>
          <Button type="button" size="sm" onClick={onApprove} disabled={reviewed}>
            <Check className="mr-1 h-3.5 w-3.5" />
            通过写入
          </Button>
        </div>
      </div>

      <p className="mt-3 text-sm leading-6 text-[#374151]">{candidate.content}</p>

      <div className="mt-3 flex flex-wrap gap-2">
        {candidate.tags.map((tag) => (
          <span key={tag} className="rounded-full bg-[#f7f8fa] px-2.5 py-1 text-xs font-semibold text-[#4b5563]">
            {tag}
          </span>
        ))}
      </div>
    </div>
  )
}
