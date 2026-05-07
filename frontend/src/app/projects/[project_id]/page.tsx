'use client'

import { useProjectStore } from '@/store/project-store'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Database, Bot, FileText, Brain, Clock, FolderOpen } from 'lucide-react'
import Link from 'next/link'
import { useApiBaseHref } from '@/lib/use-api-base-href'

export default function ProjectHomePage() {
  const { currentProject, projectState, files } = useProjectStore()
  const hrefFor = useApiBaseHref()

  if (!currentProject) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted-foreground">Loading project...</div>
      </div>
    )
  }

  const stats = [
    { label: 'Files', value: projectState?.files_count ?? 0, icon: Database },
    { label: 'Sessions', value: projectState?.sessions_count ?? 0, icon: Bot },
    { label: 'Artifacts', value: projectState?.artifacts_count ?? 0, icon: FileText },
    { label: 'Reports', value: projectState?.reports_count ?? 0, icon: FileText },
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
            Created {currentProject.created_at ? new Date(currentProject.created_at).toLocaleDateString() : 'N/A'}
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
                <CardTitle>Data Intake</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <CardDescription>
                Upload and manage your data files for analysis
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
                <CardTitle>Agent Command Center</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <CardDescription>
                Chat with the AI agent to run analysis pipelines
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
                <CardTitle>Results Dashboard</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <CardDescription>
                View analysis results and generated reports
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
                <CardTitle>Memory Review</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <CardDescription>
                Review and approve memory candidates for persistence
              </CardDescription>
            </CardContent>
          </Card>
        </Link>
      </div>

      {files.length > 0 && (
        <div className="mt-8">
          <h2 className="text-xl font-semibold mb-4">Recent Files</h2>
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
