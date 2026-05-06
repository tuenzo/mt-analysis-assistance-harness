// API Response types
export interface ApiResponse<T> {
  ok: boolean
  data: T | null
  error: string | null
}

// Project types
export interface Project {
  id: string
  name: string
  workspace_path?: string
  status: string
  current_stage?: string
  created_at?: string
  description?: string
  domain?: string
  data_source_path?: string | null
  is_test?: boolean
}

export interface ProjectState {
  files_count: number
  sessions_count: number
  artifacts_count: number
  reports_count: number
  current_stage: string
  last_activity?: string
  latest_jobs?: Array<{ id: string; action: string; status: string }>
  latest_artifacts?: Array<{ id: string; type: string; title: string }>
  latest_report?: { id: string; status: string } | null
}

export interface ProjectFile {
  id: string
  role: string
  original_name: string
  current_path: string
  status: string
  checksum: string
  mime_type?: string
  size_bytes?: number
}

export interface FileUploadResponse {
  id: string
  file_id?: string
  role: string
  original_name: string
  current_path?: string
  status: string
  checksum: string
}

export interface DataSourceResponse {
  data_source_path: string | null
}

export interface DataIngestResult {
  imported_count: number
  skipped_count: number
  source_path: string
  imported: Array<{
    file_id: string
    role: string
    original_name: string
    current_path: string
    checksum: string
  }>
  skipped: Array<{
    name: string
    reason: string
  }>
}

export interface SourceFileCandidate {
  name: string
  source_path: string
  size_bytes?: number | null
  modified_at?: string | null
  extension: string
  kind: string
  skipped: boolean
  skip_reason?: string | null
  headers: string[]
  preview: string
  preview_truncated: boolean
}

export interface DataDiscoverResult {
  source_path: string
  candidates: SourceFileCandidate[]
  candidate_count: number
}

export interface SelectedSourceFile {
  source_path: string
  role: 'order_info' | 'exposure_info' | 'activity_timeline' | 'unknown'
  reason: string
}

export interface SchemaInferResponse {
  files: Array<{
    file_id: string
    role_guess: string
    columns: Array<{
    name: string
      dtype: string
      mapped_to?: string | null
      confidence: number
    }>
  }>
}

export interface FieldMapping {
  [columnName: string]: string
}

// Agent types
export interface AgentSession {
  id: string
  project_id: string
  runtime_provider: string
  status: string
  created_at: string
}

export interface MessageResponse {
  turn_id: string
  session_id: string
  status: string
  event_stream_url: string
}

export interface AgentMessage {
  id: string
  turn_id: string
  role: 'user' | 'assistant'
  content: string
  created_at?: string
}

// SSE Event types
export type SSEEvent =
  | { type: 'assistant_message_delta'; turn_id: string; delta: string }
  | { type: 'tool_call_started'; turn_id: string; tool: string; action: string; payload?: Record<string, unknown>; tool_call_id?: string }
  | {
      type: 'tool_call_finished'
      turn_id: string
      tool: string
      action: string
      ok: boolean
      summary?: string
      tool_call_id?: string
      approval_required?: boolean
      approval_id?: string
      approval_reason?: string
      risk_level?: 'low' | 'medium' | 'high'
      approval_payload?: Record<string, unknown>
    }
  | { type: 'tool_call_failed'; turn_id: string; tool: string; action: string; error?: string; tool_call_id?: string }
  | { type: 'job_started'; turn_id: string; job_id: string; action: string }
  | { type: 'job_progress'; turn_id: string; job_id: string; progress: number; message: string }
  | { type: 'job_finished'; turn_id: string; job_id: string; ok: boolean }
  | { type: 'artifact_created'; turn_id: string; artifact_id: string; name: string; path?: string }
  | {
      type: 'approval_requested'
      turn_id: string
      approval_id: string
      action: string
      reason: string
      risk_level?: 'low' | 'medium' | 'high'
      payload?: Record<string, unknown>
    }
  | { type: 'final_answer'; turn_id: string; message: string }
  | { type: 'error'; turn_id: string; error: string }
  | { type: 'runtime_error'; turn_id: string; error: string }
  | { type: 'session_created'; turn_id: string; session_id: string }

// Artifact types
export interface Artifact {
  id: string
  project_id: string
  job_id?: string
  tool_call_id?: string
  type: string
  title: string
  path: string
  mime_type?: string
  metadata_json?: string
  checksum?: string
  created_at: string
}

export interface ArtifactsFilter {
  type?: string
  job_id?: string
  tool_call_id?: string
}

// Report types
export interface Report {
  id: string
  project_id: string
  job_id?: string
  status: string
  title?: string
  source_md_path?: string
  source_tex_path?: string
  pdf_path?: string
  docx_path?: string
  metadata_json?: string
  created_at: string
  updated_at: string
}

export interface DemoStatus {
  enabled: boolean
  project_id: string
  project_name: string
  session_id: string | null
}

export interface PendingApproval {
  id: string
  turn_id: string
  action: string
  reason: string
  risk_level: 'low' | 'medium' | 'high'
  payload: Record<string, unknown>
  created_at: string
}

export interface ApprovalActionResponse {
  result: Record<string, unknown>
  events: SSEEvent[]
}

export interface LatestReport {
  content: string
  path: string
}

// Memory types
export interface MemoryCandidate {
  id: string
  project_id: string
  session_id?: string
  turn_id?: string
  scope: string
  content: string
  source_artifact_ids?: string
  status: string
  created_at: string
  resolved_at?: string
}

export interface MemoryFilter {
  scope?: string
  status?: string
}

export interface ProjectMemory {
  content: string
  scope: string
}

export interface MemorySummaryResponse {
  summary: Record<string, unknown>
  candidate: Record<string, unknown> | null
}

export interface TimelineEntry {
  id: string
  action?: string
  status?: string
  progress?: number
  type?: string
  reason?: string
  summary?: string
  risk_level?: string
  created_at: string
  started_at?: string | null
  finished_at?: string | null
  completed_at?: string | null
  resolved_at?: string | null
  error_message?: string | null
  payload?: Record<string, unknown>
}

export interface ProjectTimeline {
  jobs: TimelineEntry[]
  tool_calls: TimelineEntry[]
  approvals: TimelineEntry[]
  events: TimelineEntry[]
}

// Notification types
export interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message?: string
  created_at: string
}
