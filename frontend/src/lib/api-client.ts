import type {
  ApiResponse,
  Project,
  ProjectState,
  ProjectFile,
  FileUploadResponse,
  DataSourceResponse,
  DataDiscoverResult,
  DataIngestResult,
  SelectedSourceFile,
  SchemaInferResponse,
  FieldMapping,
  AgentSession,
  MessageResponse,
  AgentMessage,
  DemoStatus,
  Artifact,
  ArtifactContent,
  ChartArtifactData,
  ArtifactsFilter,
  Report,
  LatestReport,
  MemoryCandidate,
  MemoryFilter,
  PendingApproval,
  ApprovalActionResponse,
  ProjectMemory,
  MemorySummaryResponse,
  ProjectTimeline,
} from './api-types'
import { API_BASE_QUERY_KEYS, API_BASE_STORAGE_KEY } from './navigation'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:18081'

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.trim().replace(/\/+$/, '')
}

class ApiClient {
  private defaultBaseUrl: string

  constructor(baseUrl: string) {
    this.defaultBaseUrl = normalizeBaseUrl(baseUrl)
  }

  getBaseUrl(): string {
    if (typeof window === 'undefined') {
      return this.defaultBaseUrl
    }

    const params = new URLSearchParams(window.location.search)
    for (const key of API_BASE_QUERY_KEYS) {
      const override = params.get(key)
      if (override?.trim()) {
        const normalized = normalizeBaseUrl(override)
        try {
          window.sessionStorage.setItem(API_BASE_STORAGE_KEY, normalized)
        } catch {
          // Ignore storage failures and keep using the query override.
        }
        return normalized
      }
    }

    try {
      const stored = window.sessionStorage.getItem(API_BASE_STORAGE_KEY)
      if (stored?.trim()) {
        return normalizeBaseUrl(stored)
      }
    } catch {
      // Ignore storage failures and fall back to the configured default.
    }

    return this.defaultBaseUrl
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.getBaseUrl()}${path}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      })

      const data = await response.json()

      if (!response.ok) {
        return {
          ok: false,
          data: null,
          error: data.detail || `HTTP ${response.status}`,
        }
      }

      return {
        ok: data.ok !== false,
        data: data.data ?? data.result ?? data,
        error: data.error || null,
      }
    } catch (error) {
      return {
        ok: false,
        data: null,
        error: error instanceof Error ? error.message : 'Network error',
      }
    }
  }

  // ===== Projects API =====
  async createProject(name: string, domain: string = 'promo_analysis', description?: string): Promise<ApiResponse<Project>> {
    return this.request<Project>('/api/projects', {
      method: 'POST',
      body: JSON.stringify({ name, domain, description }),
    })
  }

  async listProjects(): Promise<ApiResponse<Project[]>> {
    return this.request<Project[]>('/api/projects')
  }

  async getDemoStatus(): Promise<ApiResponse<DemoStatus>> {
    return this.request<DemoStatus>('/api/demo/status')
  }

  async getProject(projectId: string): Promise<ApiResponse<Project>> {
    return this.request<Project>(`/api/projects/${projectId}`)
  }

  async getProjectState(projectId: string): Promise<ApiResponse<ProjectState>> {
    return this.request<ProjectState>(`/api/projects/${projectId}/state`)
  }

  async listFiles(projectId: string): Promise<ApiResponse<ProjectFile[]>> {
    return this.request<ProjectFile[]>(`/api/projects/${projectId}/files`)
  }

  async uploadFile(projectId: string, file: File, role: string): Promise<ApiResponse<FileUploadResponse>> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('role', role)

    const response = await fetch(`${this.getBaseUrl()}/api/projects/${projectId}/files`, {
      method: 'POST',
      body: formData,
    })

    const raw = await response.json()
    const data = raw.data ?? raw
    return {
      ok: response.ok,
      data: response.ok
        ? {
            ...data,
            id: data.id ?? data.file_id,
          }
        : null,
      error: raw.error || raw.detail || null,
    }
  }

  async getDataSource(projectId: string): Promise<ApiResponse<DataSourceResponse>> {
    return this.request<DataSourceResponse>(`/api/projects/${projectId}/data-source`)
  }

  async setDataSource(projectId: string, path: string): Promise<ApiResponse<DataSourceResponse>> {
    return this.request<DataSourceResponse>(`/api/projects/${projectId}/data-source`, {
      method: 'PUT',
      body: JSON.stringify({ path }),
    })
  }

  async discoverDataSource(projectId: string, sourcePath?: string): Promise<ApiResponse<DataDiscoverResult>> {
    return this.request<DataDiscoverResult>(`/api/projects/${projectId}/data-source/discover`, {
      method: 'POST',
      body: JSON.stringify(sourcePath ? { source_path: sourcePath } : {}),
    })
  }

  async ingestDataSource(projectId: string, selectedFiles: SelectedSourceFile[], sourcePath?: string): Promise<ApiResponse<DataIngestResult>> {
    return this.request<DataIngestResult>(`/api/projects/${projectId}/data-source/ingest`, {
      method: 'POST',
      body: JSON.stringify({
        ...(sourcePath ? { source_path: sourcePath } : {}),
        selected_files: selectedFiles,
      }),
    })
  }

  async inferSchema(projectId: string): Promise<ApiResponse<SchemaInferResponse>> {
    return this.request<SchemaInferResponse>(`/api/projects/${projectId}/files/infer-schema`, {
      method: 'POST',
    })
  }

  async applySchema(projectId: string, mapping: FieldMapping): Promise<ApiResponse<void>> {
    return this.request<void>(`/api/projects/${projectId}/schema/apply`, {
      method: 'POST',
      body: JSON.stringify({ mappings: mapping }),
    })
  }

  // ===== Agent API =====
  async createMessage(projectId: string, message: string, sessionId?: string): Promise<ApiResponse<MessageResponse>> {
    return this.request<MessageResponse>('/api/agent/messages', {
      method: 'POST',
      body: JSON.stringify({
        project_id: projectId,
        session_id: sessionId,
        message,
        ui_context: {},
      }),
    })
  }

  async getSession(sessionId: string): Promise<ApiResponse<AgentSession>> {
    return this.request<AgentSession>(`/api/agent/sessions/${sessionId}`)
  }

  async getSessionMessages(sessionId: string): Promise<ApiResponse<AgentMessage[]>> {
    return this.request<AgentMessage[]>(`/api/agent/sessions/${sessionId}/messages`)
  }

  getSessionEventsUrl(sessionId: string, afterTurnId?: string | null): string {
    const url = `${this.getBaseUrl()}/api/agent/sessions/${sessionId}/events`
    if (afterTurnId) {
      return `${url}?after_turn_id=${encodeURIComponent(afterTurnId)}`
    }
    return url
  }

  async interruptSession(sessionId: string): Promise<ApiResponse<void>> {
    return this.request<void>(`/api/agent/sessions/${sessionId}/interrupt`, {
      method: 'POST',
    })
  }

  // ===== Artifacts API =====
  async listArtifacts(projectId: string, filters?: ArtifactsFilter): Promise<ApiResponse<Artifact[]>> {
    const params = new URLSearchParams()
    if (filters?.type) params.set('type', filters.type)
    if (filters?.job_id) params.set('job_id', filters.job_id)
    if (filters?.tool_call_id) params.set('tool_call_id', filters.tool_call_id)

    const queryString = params.toString()
    return this.request<Artifact[]>(
      `/api/projects/${projectId}/artifacts${queryString ? `?${queryString}` : ''}`
    )
  }

  async getArtifact(artifactId: string): Promise<ApiResponse<Artifact>> {
    return this.request<Artifact>(`/api/artifacts/${artifactId}`)
  }

  async getProjectArtifact(projectId: string, artifactId: string): Promise<ApiResponse<Artifact>> {
    return this.request<Artifact>(`/api/projects/${projectId}/artifacts/${artifactId}`)
  }

  async getArtifactContent(projectId: string, artifactId: string): Promise<ApiResponse<ArtifactContent<ChartArtifactData | string>>> {
    return this.request<ArtifactContent<ChartArtifactData | string>>(
      `/api/projects/${projectId}/artifacts/${artifactId}/content`
    )
  }

  async getArtifactContentByPath(projectId: string, path: string): Promise<ApiResponse<ArtifactContent<ChartArtifactData | string>>> {
    const params = new URLSearchParams({ path })
    return this.request<ArtifactContent<ChartArtifactData | string>>(
      `/api/projects/${projectId}/artifacts/content?${params.toString()}`
    )
  }

  // ===== Reports API =====
  async generateReport(projectId: string, reportType: string = 'standard'): Promise<ApiResponse<Report>> {
    return this.request<Report>(`/api/projects/${projectId}/reports/generate`, {
      method: 'POST',
      body: JSON.stringify({ format: reportType }),
    })
  }

  async getLatestReport(projectId: string): Promise<ApiResponse<LatestReport>> {
    return this.request<LatestReport>(`/api/projects/${projectId}/reports/latest`)
  }

  async exportReport(projectId: string, reportPath: string = '', format: string = 'md'): Promise<ApiResponse<string>> {
    return this.request<string>(`/api/projects/${projectId}/reports/export`, {
      method: 'POST',
      body: JSON.stringify({ report_path: reportPath, format }),
    })
  }

  // ===== Memory API =====
  async listMemoryCandidates(projectId: string, filters?: MemoryFilter): Promise<ApiResponse<MemoryCandidate[]>> {
    const params = new URLSearchParams()
    if (filters?.scope) params.set('scope', filters.scope)
    if (filters?.status) params.set('status', filters.status)

    const queryString = params.toString()
    return this.request<MemoryCandidate[]>(
      `/api/projects/${projectId}/memory/candidates${queryString ? `?${queryString}` : ''}`
    )
  }

  async getProjectMemory(projectId: string, scope: string = 'project'): Promise<ApiResponse<ProjectMemory[]>> {
    const params = new URLSearchParams({ scope })
    return this.request<ProjectMemory[]>(`/api/projects/${projectId}/memory?${params.toString()}`)
  }

  async generateMemorySummary(projectId: string): Promise<ApiResponse<MemorySummaryResponse>> {
    return this.request<MemorySummaryResponse>(`/api/projects/${projectId}/memory/summary`, {
      method: 'POST',
    })
  }

  async approveMemoryCandidate(candidateId: string, syncTarget: string = 'project'): Promise<ApiResponse<MemoryCandidate>> {
    return this.request<MemoryCandidate>(`/api/projects/memory/candidates/${candidateId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ sync_target: syncTarget }),
    })
  }

  async rejectMemoryCandidate(candidateId: string): Promise<ApiResponse<MemoryCandidate>> {
    return this.request<MemoryCandidate>(`/api/projects/memory/candidates/${candidateId}/reject`, {
      method: 'POST',
    })
  }

  // ===== Timeline API =====
  async getProjectTimeline(projectId: string): Promise<ApiResponse<ProjectTimeline>> {
    return this.request<ProjectTimeline>(`/api/projects/${projectId}/timeline`)
  }

  // ===== Approvals API =====
  async approveApproval(approvalId: string): Promise<ApiResponse<ApprovalActionResponse>> {
    return this.request<ApprovalActionResponse>(`/api/approvals/${approvalId}/approve`, {
      method: 'POST',
    })
  }

  async rejectApproval(approvalId: string): Promise<ApiResponse<ApprovalActionResponse>> {
    return this.request<ApprovalActionResponse>(`/api/approvals/${approvalId}/reject`, {
      method: 'POST',
    })
  }

  async listPendingApprovals(projectId: string, sessionId?: string): Promise<ApiResponse<PendingApproval[]>> {
    const params = new URLSearchParams({ project_id: projectId })
    if (sessionId) params.set('session_id', sessionId)
    return this.request<PendingApproval[]>(`/api/approvals?${params.toString()}`)
  }
}

export const api = new ApiClient(API_BASE_URL)
export default api
