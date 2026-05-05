'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import { Database, FileSpreadsheet, FolderOpen, RefreshCw, Save, Search } from 'lucide-react'
import { api } from '@/lib/api-client'
import type { DataDiscoverResult, DataIngestResult, ProjectFile, SelectedSourceFile, SourceFileCandidate } from '@/lib/api-types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

const roleOptions: SelectedSourceFile['role'][] = ['order_info', 'exposure_info', 'activity_timeline', 'unknown']

function guessRole(candidate: SourceFileCandidate): SelectedSourceFile['role'] {
  const text = `${candidate.name} ${candidate.headers.join(' ')}`.toLowerCase()
  if (text.includes('order_id') || text.includes('gmv') || text.includes('order')) return 'order_info'
  if (text.includes('exposure') || text.includes('曝光')) return 'exposure_info'
  if (text.includes('activity') || text.includes('timeline') || text.includes('payday') || text.includes('活动')) return 'activity_timeline'
  return 'unknown'
}

export default function DataIntakePage() {
  const params = useParams<{ project_id: string }>()
  const projectId = params.project_id
  const [sourcePath, setSourcePath] = useState('')
  const [files, setFiles] = useState<ProjectFile[]>([])
  const [discovery, setDiscovery] = useState<DataDiscoverResult | null>(null)
  const [selectedFiles, setSelectedFiles] = useState<SelectedSourceFile[]>([])
  const [result, setResult] = useState<DataIngestResult | null>(null)
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [discovering, setDiscovering] = useState(false)
  const [importing, setImporting] = useState(false)

  useEffect(() => {
    void refresh()
  }, [projectId])

  const importableCandidates = useMemo(
    () => discovery?.candidates.filter((candidate) => !candidate.skipped && candidate.extension === '.csv') ?? [],
    [discovery],
  )

  async function refresh() {
    const [sourceResponse, filesResponse] = await Promise.all([
      api.getDataSource(projectId),
      api.listFiles(projectId),
    ])
    if (sourceResponse.ok && sourceResponse.data) {
      setSourcePath(sourceResponse.data.data_source_path ?? '')
    }
    if (filesResponse.ok && filesResponse.data) {
      setFiles(filesResponse.data)
    }
  }

  async function saveSourcePath() {
    setSaving(true)
    setError(null)
    setStatus(null)
    const response = await api.setDataSource(projectId, sourcePath.trim())
    setSaving(false)
    if (!response.ok) {
      setError(response.error || 'Could not save data source path.')
      return
    }
    setSourcePath(response.data?.data_source_path ?? '')
    setStatus('Data source saved.')
  }

  async function discoverData() {
    setDiscovering(true)
    setError(null)
    setStatus(null)
    const response = await api.discoverDataSource(projectId)
    setDiscovering(false)
    if (!response.ok || !response.data) {
      setError(response.error || 'Could not discover source files.')
      return
    }
    setDiscovery(response.data)
    const selections = response.data.candidates
      .filter((candidate) => !candidate.skipped && candidate.extension === '.csv')
      .map((candidate) => {
        const role = guessRole(candidate)
        return {
          source_path: candidate.source_path,
          role,
          reason: role === 'unknown' ? 'Needs review before import.' : `Suggested from filename and headers: ${candidate.headers.join(', ')}`,
        }
      })
    setSelectedFiles(selections)
    setStatus(`Discovered ${response.data.candidate_count} item(s). Review roles before import.`)
  }

  async function importData() {
    setImporting(true)
    setError(null)
    setStatus(null)
    const confirmed = selectedFiles.filter((file) => file.role !== 'unknown')
    const response = await api.ingestDataSource(projectId, confirmed)
    setImporting(false)
    if (!response.ok || !response.data) {
      setError(response.error || 'Could not import selected files.')
      return
    }
    setResult(response.data)
    setStatus(`Imported ${response.data.imported_count} selected CSV file(s).`)
    await refresh()
  }

  function updateSelection(sourcePath: string, patch: Partial<SelectedSourceFile>) {
    setSelectedFiles((current) =>
      current.map((file) => (file.source_path === sourcePath ? { ...file, ...patch } : file)),
    )
  }

  function isSelected(sourcePath: string) {
    return selectedFiles.some((file) => file.source_path === sourcePath)
  }

  function toggleSelection(candidate: SourceFileCandidate) {
    setSelectedFiles((current) => {
      if (current.some((file) => file.source_path === candidate.source_path)) {
        return current.filter((file) => file.source_path !== candidate.source_path)
      }
      const role = guessRole(candidate)
      return [
        ...current,
        {
          source_path: candidate.source_path,
          role,
          reason: role === 'unknown' ? 'Selected manually; role needs review.' : `Selected from headers: ${candidate.headers.join(', ')}`,
        },
      ]
    })
  }

  return (
    <div className="container mx-auto max-w-6xl py-8 px-4 space-y-6">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-primary/10 rounded-md">
          <Database className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold">Data Intake</h1>
          <p className="text-sm text-muted-foreground">Discover local CSV candidates, review roles, then import selected files.</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Local Data Source</CardTitle>
          <CardDescription>Set an absolute directory path. Discovery reads first-level filenames, headers, and bounded previews.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-3 md:flex-row">
            <div className="relative flex-1">
              <FolderOpen className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input value={sourcePath} onChange={(event) => setSourcePath(event.target.value)} placeholder="D:\\data\\promotion_project" className="pl-9" />
            </div>
            <div className="flex gap-2">
              <Button type="button" variant="outline" onClick={saveSourcePath} disabled={saving || !sourcePath.trim()}>
                <Save className="mr-2 h-4 w-4" />
                {saving ? 'Saving' : 'Save'}
              </Button>
              <Button type="button" onClick={discoverData} disabled={discovering || !sourcePath.trim()}>
                <Search className={`mr-2 h-4 w-4 ${discovering ? 'animate-spin' : ''}`} />
                {discovering ? 'Discovering' : 'Discover Files'}
              </Button>
            </div>
          </div>
          {status && <div className="rounded-md border border-primary/20 bg-primary/5 px-3 py-2 text-sm">{status}</div>}
          {error && <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</div>}
        </CardContent>
      </Card>

      {discovery && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Discovered Candidates</CardTitle>
            <CardDescription>{importableCandidates.length} CSV candidate(s) from {discovery.source_path}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {discovery.candidates.map((candidate) => {
              const selected = selectedFiles.find((file) => file.source_path === candidate.source_path)
              return (
                <div key={candidate.source_path} className="rounded-md border p-3">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <FileSpreadsheet className="h-4 w-4 text-primary" />
                        <span className="truncate text-sm font-medium">{candidate.name}</span>
                        {candidate.skipped && <span className="rounded-md bg-secondary px-2 py-1 text-xs">{candidate.skip_reason}</span>}
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {candidate.size_bytes ?? 0} bytes · {candidate.headers.join(', ') || 'no headers'}
                      </div>
                      {candidate.preview && (
                        <pre className="mt-2 max-h-32 overflow-auto rounded-md bg-secondary p-2 text-xs whitespace-pre-wrap">{candidate.preview}</pre>
                      )}
                    </div>
                    {!candidate.skipped && candidate.extension === '.csv' && (
                      <div className="flex min-w-64 flex-col gap-2">
                        <label className="flex items-center gap-2 text-sm">
                          <input type="checkbox" checked={isSelected(candidate.source_path)} onChange={() => toggleSelection(candidate)} />
                          Import this file
                        </label>
                        {selected && (
                          <>
                            <select
                              value={selected.role}
                              onChange={(event) => updateSelection(candidate.source_path, { role: event.target.value as SelectedSourceFile['role'] })}
                              className="h-9 rounded-md border bg-background px-2 text-sm"
                            >
                              {roleOptions.map((role) => <option key={role} value={role}>{role}</option>)}
                            </select>
                            <Input value={selected.reason} onChange={(event) => updateSelection(candidate.source_path, { reason: event.target.value })} />
                          </>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
            <div className="flex justify-end">
              <Button type="button" onClick={importData} disabled={importing || selectedFiles.filter((file) => file.role !== 'unknown').length === 0}>
                <RefreshCw className={`mr-2 h-4 w-4 ${importing ? 'animate-spin' : ''}`} />
                {importing ? 'Importing' : 'Import Selected'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Latest Import</CardTitle>
            <CardDescription>Source: {result.source_path}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {result.imported.map((file) => (
              <div key={file.file_id} className="rounded-md border p-3 text-sm">
                <div className="font-medium">{file.original_name}</div>
                <div className="text-xs text-muted-foreground">{file.role} · {file.current_path}</div>
              </div>
            ))}
            {result.skipped.map((item) => (
              <div key={`${item.name}-${item.reason}`} className="rounded-md border p-3 text-sm">
                <div className="font-medium">{item.name}</div>
                <div className="text-xs text-muted-foreground">{item.reason}</div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Workspace Files</CardTitle>
          <CardDescription>Files currently registered for this project.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {files.length === 0 && <p className="text-sm text-muted-foreground">No files have been imported yet.</p>}
            {files.map((file) => (
              <div key={file.id} className="flex items-center gap-3 rounded-md border p-3">
                <FileSpreadsheet className="h-4 w-4 text-muted-foreground" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{file.original_name}</p>
                  <p className="truncate text-xs text-muted-foreground">{file.current_path}</p>
                </div>
                <span className="rounded-md bg-secondary px-2 py-1 text-xs">{file.role}</span>
                <span className="text-xs text-muted-foreground">{file.status}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
