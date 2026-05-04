import uuid
from datetime import datetime
from typing import Optional
from app.core.database import get_session
from app.projects.models import AnalysisSession


class SessionStore:
    def create_session(self, project_id: str, provider: str = "mock") -> AnalysisSession:
        db = get_session()
        try:
            session = AnalysisSession(
                id=uuid.uuid4().hex,
                project_id=project_id,
                runtime_provider=provider,
                external_session_id=uuid.uuid4().hex,
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

    def get_or_create_session(self, project_id: str, session_id: Optional[str], provider: str = "mock") -> AnalysisSession:
        if session_id:
            s = self.get_session(session_id)
            if s and s.project_id == project_id:
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
            return db.query(AnalysisSession).filter(AnalysisSession.project_id == project_id).all()
        finally:
            db.close()
