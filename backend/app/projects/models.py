import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


def new_id():
    return uuid.uuid4().hex


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(32), primary_key=True, default=new_id)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    workspace_path = Column(String(512), nullable=False)
    domain = Column(String(64), default="promo_analysis")
    status = Column(String(32), nullable=False, default="created")
    current_stage = Column(String(32), default="created")
    created_at = Column(String(32), nullable=False, default=lambda: datetime.now().isoformat())
    updated_at = Column(String(32), nullable=False, default=lambda: datetime.now().isoformat())

    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")
    sessions = relationship("AnalysisSession", back_populates="project", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="project", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="project", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="project", cascade="all, delete-orphan")
    memory_candidates = relationship("MemoryCandidate", back_populates="project", cascade="all, delete-orphan")


class ProjectFile(Base):
    __tablename__ = "project_files"

    id = Column(String(32), primary_key=True, default=new_id)
    project_id = Column(String(32), ForeignKey("projects.id"), nullable=False)
    role = Column(String(32), nullable=False)
    original_name = Column(String(255), nullable=False)
    current_path = Column(String(512), nullable=False)
    mime_type = Column(String(64), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    checksum = Column(String(128), nullable=False)
    schema_hash = Column(String(128), nullable=True)
    schema_json = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="uploaded")
    created_at = Column(String(32), nullable=False, default=lambda: datetime.now().isoformat())
    updated_at = Column(String(32), nullable=False, default=lambda: datetime.now().isoformat())

    project = relationship("Project", back_populates="files")


class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"

    id = Column(String(32), primary_key=True, default=new_id)
    project_id = Column(String(32), ForeignKey("projects.id"), nullable=False)
    runtime_provider = Column(String(64), nullable=False, default="mock")
    external_session_id = Column(String(128), nullable=True)
    status = Column(String(32), nullable=False, default="active")
    created_at = Column(String(32), nullable=False, default=lambda: datetime.now().isoformat())
    updated_at = Column(String(32), nullable=False, default=lambda: datetime.now().isoformat())

    project = relationship("Project", back_populates="sessions")
    turns = relationship("AgentTurn", back_populates="session", cascade="all, delete-orphan")


class AgentTurn(Base):
    __tablename__ = "agent_turns"

    id = Column(String(32), primary_key=True, default=new_id)
    session_id = Column(String(32), ForeignKey("analysis_sessions.id"), nullable=False)
    project_id = Column(String(32), ForeignKey("projects.id"), nullable=False)
    user_message = Column(Text, nullable=False)
    assistant_message = Column(Text, nullable=True)
    intent = Column(String(32), nullable=True)
    status = Column(String(32), nullable=False, default="running")
    created_at = Column(String(32), nullable=False, default=lambda: datetime.now().isoformat())
    completed_at = Column(String(32), nullable=True)
    error_message = Column(Text, nullable=True)

    session = relationship("AnalysisSession", back_populates="turns")
    events = relationship("AgentEvent", back_populates="turn", cascade="all, delete-orphan")
    tool_calls = relationship("ToolCall", back_populates="turn", cascade="all, delete-orphan")


class AgentEvent(Base):
    __tablename__ = "agent_events"

    id = Column(String(32), primary_key=True, default=new_id)
    session_id = Column(String(32), ForeignKey("analysis_sessions.id"), nullable=False)
    turn_id = Column(String(32), ForeignKey("agent_turns.id"), nullable=True)
    project_id = Column(String(32), ForeignKey("projects.id"), nullable=False)
    type = Column(String(64), nullable=False)
    payload_json = Column(Text, nullable=False)
    created_at = Column(String(32), nullable=False, default=lambda: datetime.now().isoformat())

    turn = relationship("AgentTurn", back_populates="events")


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(String(32), primary_key=True, default=new_id)
    session_id = Column(String(32), ForeignKey("analysis_sessions.id"), nullable=False)
    turn_id = Column(String(32), ForeignKey("agent_turns.id"), nullable=False)
    project_id = Column(String(32), ForeignKey("projects.id"), nullable=False)
    tool_name = Column(String(64), nullable=False)
    action = Column(String(64), nullable=False)
    payload_json = Column(Text, nullable=False)
    payload_hash = Column(String(128), nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="pending")
    result_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    permission_level = Column(Integer, default=0)
    approval_request_id = Column(String(32), nullable=True)
    created_at = Column(String(32), nullable=False, default=lambda: datetime.now().isoformat())
    completed_at = Column(String(32), nullable=True)

    turn = relationship("AgentTurn", back_populates="tool_calls")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(32), primary_key=True, default=new_id)
    project_id = Column(String(32), ForeignKey("projects.id"), nullable=False)
    session_id = Column(String(32), nullable=True)
    turn_id = Column(String(32), nullable=True)
    tool_call_id = Column(String(32), ForeignKey("tool_calls.id"), nullable=True)
    action = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="queued")
    progress = Column(Float, default=0)
    input_json = Column(Text, nullable=True)
    output_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(String(32), nullable=True)
    finished_at = Column(String(32), nullable=True)
    created_at = Column(String(32), nullable=False, default=lambda: datetime.now().isoformat())

    project = relationship("Project", back_populates="jobs")
    artifacts = relationship("Artifact", back_populates="job", cascade="all, delete-orphan")


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(String(32), primary_key=True, default=new_id)
    project_id = Column(String(32), ForeignKey("projects.id"), nullable=False)
    job_id = Column(String(32), ForeignKey("jobs.id"), nullable=True)
    tool_call_id = Column(String(32), ForeignKey("tool_calls.id"), nullable=True)
    type = Column(String(32), nullable=False)
    title = Column(String(255), nullable=False)
    path = Column(String(512), nullable=False)
    mime_type = Column(String(64), nullable=True)
    metadata_json = Column(Text, nullable=True)
    checksum = Column(String(128), nullable=True)
    created_at = Column(String(32), nullable=False, default=lambda: datetime.now().isoformat())

    project = relationship("Project", back_populates="artifacts")
    job = relationship("Job", back_populates="artifacts")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(32), primary_key=True, default=new_id)
    project_id = Column(String(32), ForeignKey("projects.id"), nullable=False)
    job_id = Column(String(32), ForeignKey("jobs.id"), nullable=True)
    status = Column(String(32), nullable=False, default="draft")
    title = Column(String(255), nullable=True)
    source_md_path = Column(String(512), nullable=True)
    source_tex_path = Column(String(512), nullable=True)
    pdf_path = Column(String(512), nullable=True)
    docx_path = Column(String(512), nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(String(32), nullable=False, default=lambda: datetime.now().isoformat())
    updated_at = Column(String(32), nullable=False, default=lambda: datetime.now().isoformat())

    project = relationship("Project", back_populates="reports")


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(String(32), primary_key=True, default=new_id)
    project_id = Column(String(32), ForeignKey("projects.id"), nullable=False)
    session_id = Column(String(32), nullable=True)
    turn_id = Column(String(32), nullable=True)
    tool_call_id = Column(String(32), ForeignKey("tool_calls.id"), nullable=True)
    action = Column(String(64), nullable=False)
    reason = Column(Text, nullable=True)
    risk_level = Column(String(16), nullable=False)
    payload_json = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    created_at = Column(String(32), nullable=False, default=lambda: datetime.now().isoformat())
    resolved_at = Column(String(32), nullable=True)
    resolved_by = Column(String(64), nullable=True)


class MemoryCandidate(Base):
    __tablename__ = "memory_candidates"

    id = Column(String(32), primary_key=True, default=new_id)
    project_id = Column(String(32), ForeignKey("projects.id"), nullable=False)
    session_id = Column(String(32), nullable=True)
    turn_id = Column(String(32), nullable=True)
    scope = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    source_artifact_ids = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="pending")
    created_at = Column(String(32), nullable=False, default=lambda: datetime.now().isoformat())
    resolved_at = Column(String(32), nullable=True)

    project = relationship("Project", back_populates="memory_candidates")
