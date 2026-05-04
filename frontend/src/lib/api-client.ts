import type {
  ApiResponse,
  Project,
  ProjectState,
  ProjectFile,
  FileUploadResponse,
  SchemaInferResponse,
  FieldMapping,
  AgentSession,
  MessageResponse,
  Artifact,
  ArtifactsFilter,
  Report,
  MemoryCandidate,
  MemoryFilter,
} from './api-types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
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
        data: data.data ?? data,
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

    const response = await fetch(`${this.baseUrl}/api/projects/${projectId}/files`, {
      method: 'POST',
      body: formData,
    })

    const data = await response.json()
    return {
      ok: response.ok,
      data: data,
      error: data.error || null,
    }
  }

  async inferSchema(projectId: string): Promise<ApiResponse<SchemaInferResponse>> {
    return this.request<SchemaInferResponse>(`/api/projects/${projectId}/schema/infer`, {
      method: 'POST',
    })
  }

  async applySchema(projectId: string, mapping: FieldMapping): Promise<ApiResponse<void>> {
    return this.request<void>(`/api/projects/${projectId}/schema/apply`, {
      method: 'POST',
      body: JSON.stringify({ mapping }),
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

  getSessionEventsUrl(sessionId: string): string {
    return `${this.baseUrl}/api/agent/sessions/${sessionId}/events`
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

  // ===== Reports API =====
  async generateReport(projectId: string, reportType: string = 'standard'): Promise<ApiResponse<Report>> {
    return this.request<Report>(`/api/projects/${projectId}/reports`, {
      method: 'POST',
      body: JSON.stringify({ report_type: reportType }),
    })
  }

  async getLatestReport(projectId: string): Promise<ApiResponse<Report>> {
    return this.request<Report>(`/api/projects/${projectId}/reports/latest`)
  }

  async exportReport(reportId: string, format: string): Promise<ApiResponse<string>> {
    return this.request<string>(`/api/reports/${reportId}/export?format=${format}`)
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

  async approveMemoryCandidate(candidateId: string, syncTarget: string = 'project'): Promise<ApiResponse<MemoryCandidate>> {
    return this.request<MemoryCandidate>(`/api/memory/candidates/${candidateId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ sync_target: syncTarget }),
    })
  }

  async rejectMemoryCandidate(candidateId: string): Promise<ApiResponse<MemoryCandidate>> {
    return this.request<MemoryCandidate>(`/api/memory/candidates/${candidateId}/reject`, {
      method: 'POST',
    })
  }

  // ===== Approvals API =====
  async approveApproval(approvalId: string): Promise<ApiResponse<void>> {
    return this.request<void>(`/api/approvals/${approvalId}/approve`, {
      method: 'POST',
    })
  }

  async rejectApproval(approvalId: string): Promise<ApiResponse<void>> {
    return this.request<void>(`/api/approvals/${approvalId}/reject`, {
      method: 'POST',
    })
  }
}

export const api = new ApiClient(API_BASE_URL)
export default api
