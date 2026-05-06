'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import {
  Activity,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  Clipboard,
  Database,
  FileText,
  Gauge,
  LineChart,
  Link2,
  RefreshCw,
  Scale,
  ShieldAlert,
  TableProperties,
  TrendingUp,
} from 'lucide-react'
import { api } from '@/lib/api-client'
import type { Artifact, LatestReport, ProjectState } from '@/lib/api-types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { MarkdownView } from '@/components/markdown-view'

type ReportSection = {
  heading: string
  content: string
  level: number
}

type EvidenceStatus = 'complete' | 'partial' | 'pending'

type KpiTone = 'default' | 'good' | 'watch' | 'neutral'

export default function DashboardPage() {
  const params = useParams<{ project_id: string }>()
  const projectId = params.project_id
  const [state, setState] = useState<ProjectState | null>(null)
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [report, setReport] = useState<LatestReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copiedArtifactId, setCopiedArtifactId] = useState<string | null>(null)

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    setError(null)
    const [stateResponse, artifactResponse, reportResponse] = await Promise.all([
      api.getProjectState(projectId),
      api.listArtifacts(projectId),
      api.getLatestReport(projectId),
    ])
    setLoading(false)

    if (!stateResponse.ok || !stateResponse.data) {
      setError(stateResponse.error || '加载看板状态失败。')
      setState(null)
    } else {
      setState(stateResponse.data)
    }

    setArtifacts(artifactResponse.ok && artifactResponse.data ? artifactResponse.data : [])
    setReport(reportResponse.ok && reportResponse.data ? reportResponse.data : null)
  }, [projectId])

  useEffect(() => {
    const timeout = setTimeout(() => {
      void loadDashboard()
    }, 0)
    return () => clearTimeout(timeout)
  }, [loadDashboard])

  const reportContent = report?.content ?? ''
  const sections = useMemo(() => parseMarkdownSections(reportContent), [reportContent])
  const executiveSection = useMemo(() => pickSection(sections, ['summary', 'conclusion', 'executive', 'one-page', 'one page', '摘要', '结论', '一页']), [sections])
  const localGapSection = useMemo(() => pickSection(sections, ['localgap', 'increment', 'decomposition', '增量', '分解']), [sections])
  const causalSection = useMemo(() => pickSection(sections, ['psm', 'did', 'causal', '因果']), [sections])
  const executiveReadout = executiveSection ?? pickSection(sections, ['摘要', '结论', '执行摘要'])
  const incrementSection = localGapSection ?? pickSection(sections, ['增量', '拆解', '贡献'])
  const causalReadoutSection = causalSection ?? pickSection(sections, ['因果', '方向', '净效应'])
  const limitationItems = useMemo(() => buildLimitations(sections, artifacts, state, report), [artifacts, report, sections, state])
  const nextActions = useMemo(() => buildNextActions(projectId, state, artifacts, report), [artifacts, projectId, report, state])
  const kpis = useMemo(() => buildKpis(state, artifacts, reportContent), [artifacts, reportContent, state])
  const evidenceSteps = useMemo(() => buildEvidenceSteps(state, artifacts, report), [artifacts, report, state])
  const groupedArtifacts = useMemo(() => groupArtifacts(artifacts), [artifacts])
  const latestJob = state?.latest_jobs?.[0]

  async function copyArtifactPath(artifact: Artifact) {
    try {
      await navigator.clipboard.writeText(artifact.path)
      setCopiedArtifactId(artifact.id)
      window.setTimeout(() => setCopiedArtifactId(null), 1600)
    } catch {
      setCopiedArtifactId(null)
    }
  }

  return (
    <div className="container mx-auto max-w-7xl px-4 py-8 space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold">结果看板</h1>
            <Badge variant={report ? 'default' : 'secondary'}>{report ? '报告就绪' : '等待报告'}</Badge>
            {latestJob?.status && <Badge variant="outline">{humanize(latestJob.status)}</Badge>}
          </div>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            面向业务复核展示 KPI、方法证据、产物、限制和下一步决策。
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href={`/projects/${projectId}/agent`}>
            <Button type="button" variant="outline">
              <Activity className="mr-2 h-4 w-4" />
              Agent 指挥台
            </Button>
          </Link>
          <Link href={`/projects/${projectId}/reports`}>
            <Button type="button" variant="outline">
              <FileText className="mr-2 h-4 w-4" />
              报告复核
            </Button>
          </Link>
          <Button type="button" variant="outline" onClick={loadDashboard} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {kpis.map((kpi) => (
          <KpiCard key={kpi.title} {...kpi} />
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <CardTitle className="text-base">执行摘要</CardTitle>
                <CardDescription>业务复核者可以优先采取行动的结论。</CardDescription>
              </div>
              <Badge variant={executiveReadout ? 'default' : 'secondary'}>{executiveReadout ? '来自报告' : '兜底提示'}</Badge>
            </div>
          </CardHeader>
          <CardContent>
            {loading && <p className="text-sm text-muted-foreground">正在加载结果...</p>}
            {!loading && executiveReadout && (
              <MarkdownView content={executiveReadout.content} className="rounded-md bg-secondary/30 p-4" />
            )}
            {!loading && !executiveReadout && (
              <div className="rounded-md border bg-secondary/25 p-4">
                <p className="text-sm font-medium">尚未发布执行摘要。</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  看板仍会展示 workspace 覆盖情况和已生成产物。输入数据就绪后，可让 Agent 运行或刷新完整分析 pipeline。
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">证据链</CardTitle>
            <CardDescription>由项目状态和产物推断的数据到决策覆盖情况。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {evidenceSteps.map((step) => (
              <EvidenceRow key={step.label} {...step} />
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <ResultSection
          title="增量证据"
          description="LocalGap 或增量拆解信号。"
          content={incrementSection?.content ?? ''}
          empty="最新报告中暂无增量拆解章节。"
          icon={<BarChart3 className="h-4 w-4" />}
        />
        <ResultSection
          title="因果方向"
          description="PSM-DID 或其他方向性因果证据。"
          content={causalReadoutSection?.content ?? ''}
          empty="最新报告中暂无因果方向章节。"
          icon={<Scale className="h-4 w-4" />}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">待复核限制</CardTitle>
            <CardDescription>进入决策级输出前需要确认的缺口。</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {limitationItems.map((item) => (
                <div key={item} className="flex gap-3 rounded-md border px-3 py-3 text-sm">
                  <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">下一步行动</CardTitle>
            <CardDescription>下一轮分析可直接接手的动作。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {nextActions.map((action) => (
              <Link
                key={action.label}
                href={action.href}
                className="flex items-start justify-between gap-3 rounded-md border px-3 py-3 text-sm transition-colors hover:border-primary/50 hover:bg-secondary/30"
              >
                <div className="min-w-0">
                  <div className="font-medium">{action.label}</div>
                  <div className="mt-1 text-xs text-muted-foreground">{action.detail}</div>
                </div>
                <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
              </Link>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className="text-base">证据产物索引</CardTitle>
              <CardDescription>支撑当前看板结论的生成文件。</CardDescription>
            </div>
            <Badge variant="outline">{artifacts.length} 个产物</Badge>
          </div>
        </CardHeader>
        <CardContent>
          {artifacts.length === 0 ? (
            <p className="rounded-md border bg-secondary/25 p-4 text-sm text-muted-foreground">
              暂无已注册的生成产物。
            </p>
          ) : (
            <div className="grid gap-4 xl:grid-cols-2">
              {Object.entries(groupedArtifacts).map(([group, items]) => (
                <div key={group} className="space-y-2">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
                    <Link2 className="h-3.5 w-3.5" />
                    {group}
                  </div>
                  <div className="space-y-2">
                    {items.map((artifact) => (
                      <ArtifactRow
                        key={artifact.id}
                        artifact={artifact}
                        projectId={projectId}
                        copied={copiedArtifactId === artifact.id}
                        onCopy={() => void copyArtifactPath(artifact)}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function KpiCard({
  title,
  value,
  detail,
  icon,
  tone,
}: {
  title: string
  value: string
  detail: string
  icon: ReactNode
  tone: KpiTone
}) {
  const toneClass = {
    default: 'bg-primary/10 text-primary',
    good: 'bg-green-500/10 text-green-700',
    watch: 'bg-amber-500/10 text-amber-700',
    neutral: 'bg-secondary text-muted-foreground',
  }[tone]

  return (
    <Card>
      <CardContent className="flex min-h-32 items-start justify-between gap-4 p-4">
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground">{title}</p>
          <p className="mt-2 break-words text-xl font-semibold leading-tight">{value}</p>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">{detail}</p>
        </div>
        <div className={`rounded-md p-2 ${toneClass}`}>{icon}</div>
      </CardContent>
    </Card>
  )
}

function EvidenceRow({
  label,
  detail,
  status,
}: {
  label: string
  detail: string
  status: EvidenceStatus
}) {
  const icon =
    status === 'complete' ? (
      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-600" />
    ) : status === 'partial' ? (
      <Activity className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
    ) : (
      <Gauge className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
  )
  const badgeVariant = status === 'complete' ? 'default' : status === 'partial' ? 'outline' : 'secondary'
  const statusLabel: Record<EvidenceStatus, string> = {
    complete: '完成',
    partial: '部分完成',
    pending: '待处理',
  }

  return (
    <div className="flex gap-3 rounded-md border px-3 py-3">
      {icon}
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-3">
          <p className="truncate text-sm font-medium">{label}</p>
          <Badge variant={badgeVariant}>{statusLabel[status]}</Badge>
        </div>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">{detail}</p>
      </div>
    </div>
  )
}

function ResultSection({
  title,
  description,
  content,
  empty,
  icon,
}: {
  title: string
  description: string
  content: string
  empty: string
  icon: ReactNode
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start gap-3">
          <div className="rounded-md bg-primary/10 p-2 text-primary">{icon}</div>
          <div>
            <CardTitle className="text-base">{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {content ? (
          <MarkdownView content={content} className="rounded-md bg-secondary/30 p-4" />
        ) : (
          <p className="rounded-md border bg-secondary/25 p-4 text-sm text-muted-foreground">{empty}</p>
        )}
      </CardContent>
    </Card>
  )
}

function ArtifactRow({
  artifact,
  projectId,
  copied,
  onCopy,
}: {
  artifact: Artifact
  projectId: string
  copied: boolean
  onCopy: () => void
}) {
  const isReport = artifact.type === 'report' || artifact.path.toLowerCase().endsWith('.md')
  const metadata = parseArtifactMetadata(artifact.metadata_json)

  return (
    <div id={`artifact-${artifact.id}`} className="flex items-start justify-between gap-3 rounded-md border px-3 py-3">
      <div className="flex min-w-0 items-start gap-2">
        {artifact.type === 'chart' ? (
          <LineChart className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
        ) : artifact.type === 'table' ? (
          <TableProperties className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
        ) : (
          <FileText className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
        )}
        <div className="min-w-0">
          {isReport ? (
            <Link href={`/projects/${projectId}/reports`} className="block truncate text-sm font-medium text-primary underline-offset-2 hover:underline">
              {artifact.title}
            </Link>
          ) : (
            <p className="truncate text-sm font-medium">{artifact.title}</p>
          )}
          <p className="mt-1 break-all font-mono text-xs text-muted-foreground">{artifact.path}</p>
          {metadata && <p className="mt-1 text-xs text-muted-foreground">{metadata}</p>}
        </div>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-2">
        <Badge variant={artifact.type === 'report' ? 'default' : 'secondary'}>{artifact.type}</Badge>
        <button
          type="button"
          onClick={onCopy}
          className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs transition-colors hover:bg-secondary"
          title="复制产物路径"
        >
          <Clipboard className="h-3.5 w-3.5" />
          {copied ? '已复制' : '路径'}
        </button>
        <span className="text-xs text-muted-foreground">{formatTime(artifact.created_at)}</span>
      </div>
    </div>
  )
}

function buildKpis(state: ProjectState | null, artifacts: Artifact[], reportContent: string) {
  const latestStatus = state?.latest_jobs?.[0]?.status
  const totalGmv = extractMetric(reportContent, [
    /total[_\s-]*gmv\s*[:=]\s*([0-9,.+-]+)/i,
    /total\s+gmv\s*[:=]\s*([0-9,.+-]+)/i,
    /总\s*GMV\s*[:：]\s*([0-9,.+-]+)/i,
  ])
  const increment = extractMetric(reportContent, [
    /total[_\s-]*local[_\s-]*gap\s*[:=]\s*([0-9,.+-]+)/i,
    /localgap\s*[:=]\s*([0-9,.+-]+)/i,
    /总增量\s*[:：]\s*([0-9,.+-]+)/,
    /总\s*增量\s*[:：]\s*([0-9,.+-]+)/,
  ])
  const didEstimate = extractMetric(reportContent, [
    /did[_\s-]*estimate\s*[:=]\s*([0-9,.+-]+)/i,
    /did\s*(?:estimate|effect)?\s*[:=]\s*([0-9,.+-]+)/i,
    /净效应\s*[:：]?\s*([0-9,.+-]+)/,
  ])

  return [
    {
      title: '分析阶段',
      value: humanize(state?.current_stage || 'unknown'),
      detail: latestStatus ? `最近任务：${humanize(latestStatus)}` : '暂无已注册的近期 pipeline 任务。',
      icon: <Gauge className="h-4 w-4" />,
      tone: state?.current_stage === 'report_ready' ? 'good' as const : 'neutral' as const,
    },
    {
      title: '数据覆盖',
      value: `${state?.files_count ?? 0} 个文件`,
      detail: `${artifacts.length || state?.artifacts_count || 0} 个产物可供复核。`,
      icon: <Database className="h-4 w-4" />,
      tone: (state?.files_count ?? 0) >= 3 ? 'good' as const : 'watch' as const,
    },
    {
      title: 'GMV 信号',
      value: totalGmv ? formatNumberText(totalGmv) : '未报告',
      detail: totalGmv ? '从最新报告中解析。' : '运行 diagnostics 或刷新报告以暴露该 KPI。',
      icon: <TrendingUp className="h-4 w-4" />,
      tone: totalGmv ? 'default' as const : 'neutral' as const,
    },
    {
      title: '增量 / DID',
      value: increment ? formatNumberText(increment) : didEstimate ? formatNumberText(didEstimate) : '待处理',
      detail: increment ? '报告中已呈现 LocalGap 增量。' : didEstimate ? '报告中已呈现 DID 估计。' : '尚未找到增量或 DID 数值。',
      icon: <BarChart3 className="h-4 w-4" />,
      tone: increment || didEstimate ? 'default' as const : 'watch' as const,
    },
  ]
}

function buildEvidenceSteps(state: ProjectState | null, artifacts: Artifact[], report: LatestReport | null) {
  const filesCount = state?.files_count ?? 0
  const hasPanel = hasArtifact(artifacts, ['panel', 'category_day_panel', 'category_date_panel'])
  const hasDiagnostics = hasArtifact(artifacts, ['diagnostics', 'gmv_trend', 'category_concentration'])
  const hasCausal = hasArtifact(artifacts, ['psm', 'did', 'causal'])
  const hasLocalGap = hasArtifact(artifacts, ['localgap', 'local_gap'])
  const hasReport = Boolean(report)

  return [
    {
      label: '输入数据',
      status: filesCount >= 3 ? 'complete' as const : filesCount > 0 ? 'partial' as const : 'pending' as const,
      detail: filesCount >= 3 ? `${filesCount} 个已注册文件覆盖预期接入集。` : `发现 ${filesCount} 个已注册文件；订单、曝光和活动数据可能不完整。`,
    },
    {
      label: 'Panel 构建',
      status: hasPanel ? 'complete' as const : filesCount > 0 ? 'partial' as const : 'pending' as const,
      detail: hasPanel ? 'category-day panel 产物已可用。' : '当前产物索引中暂无 panel 产物。',
    },
    {
      label: '描述性诊断',
      status: hasDiagnostics ? 'complete' as const : hasPanel ? 'partial' as const : 'pending' as const,
      detail: hasDiagnostics ? '趋势、集中度或 diagnostics 产物已可用。' : '描述性证据尚未注册为产物。',
    },
    {
      label: '因果方向',
      status: hasCausal ? 'complete' as const : hasDiagnostics ? 'partial' as const : 'pending' as const,
      detail: hasCausal ? 'PSM-DID 或因果方向产物已可用。' : '方法产物注册前，因果结论只能作为方向性判断。',
    },
    {
      label: '增量拆解',
      status: hasLocalGap ? 'complete' as const : hasDiagnostics ? 'partial' as const : 'pending' as const,
      detail: hasLocalGap ? 'LocalGap 证据可用于贡献复核。' : '尚未注册 LocalGap 产物。',
    },
    {
      label: '报告与交接',
      status: hasReport ? 'complete' as const : hasLocalGap ? 'partial' as const : 'pending' as const,
      detail: hasReport ? '最新 Markdown 报告已可复核。' : '核心分析产物准备好后再生成报告。',
    },
  ]
}

function buildLimitations(
  sections: ReportSection[],
  artifacts: Artifact[],
  state: ProjectState | null,
  report: LatestReport | null,
) {
  const limitationSection = pickSection(sections, ['limitation', 'limits', 'caveat', 'assumption', 'risk', '局限', '假设', '风险'])
  const fromReport = limitationSection ? extractBullets(limitationSection.content).slice(0, 4) : []
  const cnLimitationSection = pickSection(sections, ['限制', '假设', '风险'])
  const cnFromReport = cnLimitationSection ? extractBullets(cnLimitationSection.content).slice(0, 4) : []
  if (fromReport.length > 0) return fromReport
  if (cnFromReport.length > 0) return cnFromReport

  const items: string[] = []
  if ((state?.files_count ?? 0) < 3) {
    items.push('预期的订单、曝光和活动时间线文件尚未全部注册。')
  }
  if (!hasArtifact(artifacts, ['psm', 'did', 'causal'])) {
    items.push('尚未注册因果方向产物，因此 lift 结论应保持方向性表述。')
  }
  if (!hasArtifact(artifacts, ['localgap', 'local_gap'])) {
    items.push('尚未注册 LocalGap 产物，因此增量归因还不能审计。')
  }
  if (!report) {
    items.push('暂无最新报告，因此结论还没有打包成业务复核材料。')
  }
  if (items.length === 0) {
    items.push('用于生产决策前，仍需检查毛利、缺货、活动日历和留存控制。')
  }
  return items.slice(0, 4)
}

function buildNextActions(projectId: string, state: ProjectState | null, artifacts: Artifact[], report: LatestReport | null) {
  if ((state?.files_count ?? 0) === 0) {
    return [
      {
        label: '导入源 CSV',
        detail: '先接入订单、曝光和活动时间线数据。',
        href: `/projects/${projectId}/data-intake`,
      },
      {
        label: '让 Agent 校验 schema',
        detail: '下一条自然语言请求仍通过 message runtime 路由。',
        href: `/projects/${projectId}/agent`,
      },
    ]
  }

  if (!hasArtifact(artifacts, ['panel', 'category_day_panel', 'category_date_panel'])) {
    return [
      {
        label: '构建 category-day panel',
        detail: 'schema 检查后让 Agent 运行 panel.build_category_day。',
        href: `/projects/${projectId}/agent`,
      },
      {
        label: '复核数据接入',
        detail: '分析运行前确认每个文件角色。',
        href: `/projects/${projectId}/data-intake`,
      },
    ]
  }

  if (!report) {
    return [
      {
        label: '生成业务报告',
        detail: '让 Agent 执行已批准的完整 pipeline 或刷新报告。',
        href: `/projects/${projectId}/agent`,
      },
      {
        label: '检查运行历史',
        detail: '查看 jobs、approvals 和工具输出中的阻塞点。',
        href: `/projects/${projectId}/timeline`,
      },
    ]
  }

  return [
    {
      label: '复核完整报告',
      detail: '在报告复核页检查结论、证据和缺口。',
      href: `/projects/${projectId}/reports`,
    },
    {
      label: '检查时间线',
      detail: '确认哪些已批准任务生成了当前展示结果。',
      href: `/projects/${projectId}/timeline`,
    },
    {
      label: '沉淀稳定结论',
      detail: '保留项目级结论前先复核 memory candidates。',
      href: `/projects/${projectId}/memory`,
    },
  ]
}

function groupArtifacts(artifacts: Artifact[]) {
  return artifacts.reduce<Record<string, Artifact[]>>((groups, artifact) => {
    const group = artifactGroupLabel(artifact)
    groups[group] = groups[group] ?? []
    groups[group].push(artifact)
    return groups
  }, {})
}

function artifactGroupLabel(artifact: Artifact) {
  const key = `${artifact.type} ${artifact.path} ${artifact.title}`.toLowerCase()
  if (key.includes('report')) return '报告'
  if (key.includes('chart') || key.includes('trend')) return '图表'
  if (key.includes('table') || key.includes('.csv')) return '表格'
  if (key.includes('localgap') || key.includes('diagnostics') || key.includes('psm') || key.includes('panel')) return '分析输出'
  return '其他产物'
}

function hasArtifact(artifacts: Artifact[], needles: string[]) {
  return artifacts.some((artifact) => {
    const haystack = `${artifact.type} ${artifact.title} ${artifact.path}`.toLowerCase()
    return needles.some((needle) => haystack.includes(needle.toLowerCase()))
  })
}

function parseMarkdownSections(content: string): ReportSection[] {
  if (!content.trim()) return []
  const lines = content.split(/\r?\n/)
  const sections: ReportSection[] = []
  let current: ReportSection | null = null

  for (const line of lines) {
    const match = /^(#{1,3})\s+(.+?)\s*$/.exec(line.trim())
    if (match) {
      if (current) sections.push(current)
      current = {
        heading: match[2],
        level: match[1].length,
        content: line,
      }
      continue
    }

    if (current) {
      current.content += `\n${line}`
    }
  }

  if (current) sections.push(current)
  if (sections.length === 0) {
    return [{ heading: '最新报告', level: 1, content }]
  }
  return sections
}

function pickSection(sections: ReportSection[], keywords: string[]) {
  const normalized = keywords.map((keyword) => keyword.toLowerCase())
  return sections.find((section) => {
    const heading = section.heading.toLowerCase()
    return normalized.some((keyword) => heading.includes(keyword))
  })
}

function extractBullets(content: string) {
  return content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => /^[-*]\s+/.test(line) || /^\d+\.\s+/.test(line))
    .map((line) => line.replace(/^[-*]\s+/, '').replace(/^\d+\.\s+/, '').replace(/\*\*/g, '').trim())
    .filter(Boolean)
}

function extractMetric(content: string, patterns: RegExp[]) {
  for (const pattern of patterns) {
    const match = content.match(pattern)
    if (match?.[1]) return match[1]
  }
  return ''
}

function parseArtifactMetadata(value?: string) {
  if (!value) return ''
  try {
    const parsed = JSON.parse(value) as Record<string, unknown>
    const labels = Object.entries(parsed)
      .filter(([, item]) => typeof item === 'string' || typeof item === 'number' || typeof item === 'boolean')
      .slice(0, 2)
      .map(([key, item]) => `${humanize(key)}: ${String(item)}`)
    return labels.join(' | ')
  } catch {
    return ''
  }
}

function formatNumberText(value: string) {
  const cleaned = value.replace(/,/g, '')
  const parsed = Number(cleaned)
  if (!Number.isFinite(parsed)) return value
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(parsed)
}

function humanize(value: string) {
  const labels: Record<string, string> = {
    report_ready: '报告就绪',
    succeeded: '成功',
    completed: '完成',
    failed: '失败',
    running: '运行中',
    pending: '等待中',
    unknown: '未知',
  }
  if (labels[value]) return labels[value]
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase()) || '未知'
}

function formatTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '--'
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}
