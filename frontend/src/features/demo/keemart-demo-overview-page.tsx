'use client'

import Link from 'next/link'
import type { ReactNode } from 'react'
import { Bot, Database, FileBarChart, FileText, Layers, Target } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useApiBaseHref } from '@/lib/use-api-base-href'
import { KEEMART_PROJECT_ID, keemartReportFacts } from '@/features/demo/keemart-demo-data'

export function KeemartDemoOverviewPage() {
  const hrefFor = useApiBaseHref()

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-bold text-muted-foreground">周期性促销分析项目</p>
          <h1 className="mt-2 text-3xl font-bold">Keemart 沙特月末促销复盘</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
            该项目围绕沙特月末发薪窗口下的促销活动，组织数据接入、Agent 分析、结果看板和报告复盘。
          </p>
        </div>
        <div className="flex gap-2">
          <Link href={hrefFor(`/projects/${KEEMART_PROJECT_ID}/agent`)}>
            <Button>
              <Bot className="mr-2 h-4 w-4" />
              Agent 分析
            </Button>
          </Link>
          <Link href={hrefFor(`/projects/${KEEMART_PROJECT_ID}/dashboard`)}>
            <Button variant="outline">
              <FileBarChart className="mr-2 h-4 w-4" />
              结果看板
            </Button>
          </Link>
        </div>
      </div>

      <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
        <MetricCard label="观测区间" value="2025.09-11" icon={<Database className="h-4 w-4" />} />
        <MetricCard label="活动窗口" value={`${keemartReportFacts.activityWindows} 个 / ${keemartReportFacts.activityDays} 天`} icon={<Target className="h-4 w-4" />} />
        <MetricCard label="品类面板" value={`${keemartReportFacts.categoryCount} 个`} icon={<Layers className="h-4 w-4" />} />
        <MetricCard label="支付用户" value={keemartReportFacts.paidUsers.toLocaleString('en-US')} icon={<FileText className="h-4 w-4" />} />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Link href={hrefFor(`/projects/${KEEMART_PROJECT_ID}/agent`)}>
          <Card className="cursor-pointer transition-colors hover:border-primary/60">
            <CardHeader>
              <CardTitle>Agent 分析中心</CardTitle>
              <CardDescription>回放自然语言需求、工具调用链路和最终业务解释。</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">重点展示：data.validate、panel.build_category_day、PSM-DID、GMV 拆解、GPS/Uplift 和策略生成。</p>
            </CardContent>
          </Card>
        </Link>
        <Link href={hrefFor(`/projects/${KEEMART_PROJECT_ID}/dashboard`)}>
          <Card className="cursor-pointer transition-colors hover:border-primary/60">
            <CardHeader>
              <CardTitle>结果看板</CardTitle>
              <CardDescription>用报告真实结论填充现有 Dashboard 结构。</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">核心指标：实际 GMV、反事实 GMV、净增量、订单量贡献、客单价贡献和 Uplift 投放策略。</p>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  )
}

function MetricCard({ label, value, icon }: { label: string; value: string; icon: ReactNode }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{label}</CardTitle>
        <span className="text-muted-foreground">{icon}</span>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
      </CardContent>
    </Card>
  )
}
