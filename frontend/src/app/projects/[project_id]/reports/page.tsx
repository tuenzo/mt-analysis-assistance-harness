'use client'

import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { FileText, RefreshCw } from 'lucide-react'
import { api } from '@/lib/api-client'
import type { LatestReport } from '@/lib/api-types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { MarkdownView } from '@/components/markdown-view'

export default function ReportsPage() {
  const params = useParams<{ project_id: string }>()
  const projectId = params.project_id
  const [report, setReport] = useState<LatestReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadReport = useCallback(async () => {
    setLoading(true)
    setError(null)
    const response = await api.getLatestReport(projectId)
    setLoading(false)
    if (!response.ok || !response.data) {
      setReport(null)
      setError(response.error || 'No report is available yet.')
      return
    }
    setReport(response.data)
  }, [projectId])

  useEffect(() => {
    const timeout = setTimeout(() => {
      void loadReport()
    }, 0)
    return () => clearTimeout(timeout)
  }, [loadReport])

  return (
    <div className="container mx-auto max-w-5xl py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-md bg-primary/10 p-2">
            <FileText className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold">Report Studio</h1>
            <p className="text-sm text-muted-foreground">View the latest generated analysis report.</p>
          </div>
        </div>
        <Button type="button" variant="outline" onClick={loadReport} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{report ? 'Latest Report' : 'No Report Loaded'}</CardTitle>
          <CardDescription>{report?.path || 'Generate or seed a report to view it here.'}</CardDescription>
        </CardHeader>
        <CardContent>
          {loading && <p className="text-sm text-muted-foreground">Loading report...</p>}
          {!loading && error && <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</div>}
          {!loading && report && (
            <div className="max-h-[70vh] overflow-auto rounded-md bg-secondary/30 p-4">
              <MarkdownView content={report.content} />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
