import uuid
from datetime import datetime
from typing import Optional
from app.core.database import get_session
from app.projects.models import (
    AgentEvent,
    AgentTurn,
    AnalysisSession,
    ApprovalRequest,
    Artifact,
    Job,
    MemoryCandidate,
    ToolCall,
)


class SessionStore:
    def create_session(
        self,
        project_id: str,
        provider: str = "mock",
        external_session_id: str | None = None,
    ) -> AnalysisSession:
        db = get_session()
        try:
            session = AnalysisSession(
                id=uuid.uuid4().hex,
                project_id=project_id,
                runtime_provider=provider,
                external_session_id=external_session_id or uuid.uuid4().hex,
                status="active",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            return session
        finally:
            db.close()

    def get_session(self, session_id: str) -> Optional[AnalysisSession]:
        db = get_session()
        try:
            return db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
        finally:
            db.close()

    def get_session_summary(self, session_id: str) -> dict | None:
        db = get_session()
        try:
            session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
            if not session:
                return None
            return self._session_summary(db, session)
        finally:
            db.close()

    def get_or_create_session(self, project_id: str, session_id: Optional[str], provider: str = "mock") -> AnalysisSession:
        if session_id:
            s = self.get_session(session_id)
            if s and s.project_id == project_id:
                self.update_session(s.id)
                return s
        return self.create_session(project_id, provider)

    def update_session(self, session_id: str, **kwargs) -> None:
        db = get_session()
        try:
            session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
            if session:
                for key, value in kwargs.items():
                    if hasattr(session, key):
                        setattr(session, key, value)
                session.updated_at = datetime.now().isoformat()
                db.commit()
        finally:
            db.close()

    def list_project_sessions(self, project_id: str) -> list[AnalysisSession]:
        db = get_session()
        try:
            return (
                db.query(AnalysisSession)
                .filter(AnalysisSession.project_id == project_id)
                .order_by(
                    AnalysisSession.updated_at.desc(),
                    AnalysisSession.created_at.desc(),
                    AnalysisSession.id.desc(),
                )
                .all()
            )
        finally:
            db.close()

    def list_project_session_summaries(self, project_id: str) -> list[dict]:
        db = get_session()
        try:
            sessions = (
                db.query(AnalysisSession)
                .filter(AnalysisSession.project_id == project_id)
                .order_by(
                    AnalysisSession.updated_at.desc(),
                    AnalysisSession.created_at.desc(),
                    AnalysisSession.id.desc(),
                )
                .all()
            )
            summaries = [self._session_summary(db, session) for session in sessions]
            return sorted(
                summaries,
                key=lambda item: (item.get("last_activity_at") or item.get("updated_at") or item.get("created_at") or "", item["id"]),
                reverse=True,
            )
        finally:
            db.close()

    def delete_session(self, session_id: str) -> dict | None:
        db = get_session()
        try:
            session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
            if not session:
                return None

            project_id = session.project_id
            turn_ids = [
                row[0]
                for row in db.query(AgentTurn.id).filter(AgentTurn.session_id == session_id).all()
            ]
            tool_call_ids = [
                row[0]
                for row in db.query(ToolCall.id).filter(ToolCall.session_id == session_id).all()
            ]
            job_ids = [
                row[0]
                for row in db.query(Job.id).filter(Job.session_id == session_id).all()
            ]
            delete_options = {"synchronize_session": False}

            if tool_call_ids:
                db.query(Artifact).filter(Artifact.tool_call_id.in_(tool_call_ids)).update(
                    {Artifact.tool_call_id: None},
                    **delete_options,
                )
                db.query(ApprovalRequest).filter(ApprovalRequest.tool_call_id.in_(tool_call_ids)).delete(**delete_options)
            if job_ids:
                db.query(Job).filter(Job.id.in_(job_ids)).update(
                    {Job.session_id: None, Job.turn_id: None, Job.tool_call_id: None},
                    **delete_options,
                )
            if turn_ids:
                db.query(MemoryCandidate).filter(MemoryCandidate.turn_id.in_(turn_ids)).update(
                    {MemoryCandidate.session_id: None, MemoryCandidate.turn_id: None},
                    **delete_options,
                )
                db.query(ApprovalRequest).filter(ApprovalRequest.turn_id.in_(turn_ids)).delete(**delete_options)

            db.query(MemoryCandidate).filter(MemoryCandidate.session_id == session_id).update(
                {MemoryCandidate.session_id: None, MemoryCandidate.turn_id: None},
                **delete_options,
            )
            db.query(ApprovalRequest).filter(ApprovalRequest.session_id == session_id).delete(**delete_options)
            db.query(AgentEvent).filter(AgentEvent.session_id == session_id).delete(**delete_options)
            db.query(ToolCall).filter(ToolCall.session_id == session_id).delete(**delete_options)
            db.query(AgentTurn).filter(AgentTurn.session_id == session_id).delete(**delete_options)
            db.delete(session)
            db.commit()
            return {"id": session_id, "project_id": project_id, "deleted": True}
        finally:
            db.close()

    @staticmethod
    def _session_summary(db, session: AnalysisSession) -> dict:
        turns = (
            db.query(AgentTurn)
            .filter(AgentTurn.session_id == session.id)
            .order_by(AgentTurn.created_at.asc(), AgentTurn.id.asc())
            .all()
        )
        message_count = sum(1 + (1 if turn.assistant_message else 0) for turn in turns)
        last_turn = turns[-1] if turns else None
        last_message = ""
        last_activity_at = session.updated_at or session.created_at
        if last_turn:
            last_message = last_turn.assistant_message or last_turn.user_message or ""
            last_activity_at = last_turn.completed_at or last_turn.created_at or last_activity_at

        return {
            "id": session.id,
            "project_id": session.project_id,
            "runtime_provider": session.runtime_provider,
            "status": session.status,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "last_activity_at": last_activity_at,
            "message_count": message_count,
            "last_message": last_message,
        }
