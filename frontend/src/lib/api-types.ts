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
}

export interface ProjectState {
  files_count: number
  sessions_count: number
  artifacts_count: number
  reports_count: number
  current_stage: string
  last_activity?: string
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
  role: string
  original_name: string
  current_path: string
  status: string
  checksum: string
}

export interface SchemaInferResponse {
  fields: Array<{
    name: string
    inferred_type: string
    nullable: boolean
    sample_values: string[]
  }>
  suggested_mappings: Record<string, string>
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
  | { type: 'tool_call_started'; turn_id: string; tool: string; action: string; payload?: Record<string, unknown> }
  | { type: 'tool_call_finished'; turn_id: string; tool: string; action: string; ok: boolean; summary?: string }
  | { type: 'tool_call_failed'; turn_id: string; tool: string; action: string; error?: string }
  | { type: 'job_started'; turn_id: string; job_id: string; action: string }
  | { type: 'job_progress'; turn_id: string; job_id: string; progress: number; message: string }
  | { type: 'job_finished'; turn_id: string; job_id: string; ok: boolean }
  | { type: 'artifact_created'; turn_id: string; artifact_id: string; name: string; path?: string }
  | { type: 'approval_requested'; turn_id: string; approval_id: string; action: string; reason: string }
  | { type: 'final_answer'; turn_id: string; message: string }
  | { type: 'error'; turn_id: string; error: string }
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

// Notification types
export interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message?: string
  created_at: string
}
