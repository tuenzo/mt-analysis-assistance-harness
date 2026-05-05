'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { FileText, RefreshCw } from 'lucide-react'
import { api } from '@/lib/api-client'
import type { LatestReport } from '@/lib/api-types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function ReportsPage() {
  const params = useParams<{ project_id: string }>()
  const projectId = params.project_id
  const [report, setReport] = useState<LatestReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function loadReport() {
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
  }

  useEffect(() => {
    void loadReport()
  }, [projectId])

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
            <pre className="max-h-[70vh] overflow-auto whitespace-pre-wrap rounded-md bg-secondary/40 p-4 text-sm leading-6">
              {report.content}
            </pre>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
