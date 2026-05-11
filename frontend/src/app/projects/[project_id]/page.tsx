'use client'

import { useProjectStore } from '@/store/project-store'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Database, Bot, FileText, Brain, Clock, FolderOpen } from 'lucide-react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { useApiBaseHref } from '@/lib/use-api-base-href'
import { isKeemartPromoProject } from '@/features/demo/keemart-demo-data'
import { KeemartDemoOverviewPage } from '@/features/demo/keemart-demo-overview-page'

export default function ProjectHomePage() {
  const params = useParams<{ project_id: string }>()
  const { currentProject, projectState, files } = useProjectStore()
  const hrefFor = useApiBaseHref()

  if (isKeemartPromoProject(params.project_id)) {
    return <KeemartDemoOverviewPage />
  }

  if (!currentProject) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted-foreground">正在加载项目...</div>
      </div>
    )
  }

  const stats = [
    { label: '文件', value: projectState?.files_count ?? 0, icon: Database },
    { label: '会话', value: projectState?.sessions_count ?? 0, icon: Bot },
    { label: '产物', value: projectState?.artifacts_count ?? 0, icon: FileText },
    { label: '报告', value: projectState?.reports_count ?? 0, icon: FileText },
  ]

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">{currentProject.name}</h1>
        {currentProject.description && (
          <p className="text-muted-foreground mt-2">{currentProject.description}</p>
        )}
        <div className="flex items-center gap-4 mt-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <Clock className="h-4 w-4" />
            创建于 {currentProject.created_at ? new Date(currentProject.created_at).toLocaleDateString() : '暂无'}
          </span>
          <span className="px-2 py-0.5 bg-secondary rounded-full">
            {currentProject.status}
          </span>
          {currentProject.current_stage && (
            <span className="px-2 py-0.5 bg-primary/10 text-primary rounded-full">
              {currentProject.current_stage}
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <Card key={stat.label}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{stat.label}</CardTitle>
                <Icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Link href={hrefFor(`/projects/${currentProject.id}/data-intake`)}>
          <Card className="hover:border-primary/50 transition-colors cursor-pointer">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <Database className="h-5 w-5 text-primary" />
                </div>
                <CardTitle>数据接入</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <CardDescription>
                上传、发现并管理用于分析的数据文件。
              </CardDescription>
            </CardContent>
          </Card>
        </Link>

        <Link href={hrefFor(`/projects/${currentProject.id}/agent`)}>
          <Card className="hover:border-primary/50 transition-colors cursor-pointer">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <Bot className="h-5 w-5 text-primary" />
                </div>
                <CardTitle>Agent 分析中心</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <CardDescription>
                通过对话驱动数据校验、分析管道与结果解释。
              </CardDescription>
            </CardContent>
          </Card>
        </Link>

        <Link href={hrefFor(`/projects/${currentProject.id}/dashboard`)}>
          <Card className="hover:border-primary/50 transition-colors cursor-pointer">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <FileText className="h-5 w-5 text-primary" />
                </div>
                <CardTitle>结果看板</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <CardDescription>
                查看分析结果、关键指标和生成的报告产物。
              </CardDescription>
            </CardContent>
          </Card>
        </Link>

        <Link href={hrefFor(`/projects/${currentProject.id}/memory`)}>
          <Card className="hover:border-primary/50 transition-colors cursor-pointer">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <Brain className="h-5 w-5 text-primary" />
                </div>
                <CardTitle>记忆审核</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <CardDescription>
                审核并确认需要沉淀到项目记忆的候选内容。
              </CardDescription>
            </CardContent>
          </Card>
        </Link>
      </div>

      {files.length > 0 && (
        <div className="mt-8">
          <h2 className="text-xl font-semibold mb-4">最近文件</h2>
          <div className="space-y-2">
            {files.slice(0, 5).map((file) => (
              <div key={file.id} className="flex items-center gap-3 p-3 bg-card border rounded-lg">
                <FolderOpen className="h-4 w-4 text-muted-foreground" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{file.original_name}</p>
                  <p className="text-xs text-muted-foreground">{file.role}</p>
                </div>
                <span className="text-xs text-muted-foreground">{file.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
