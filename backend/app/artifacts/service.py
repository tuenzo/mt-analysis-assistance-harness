import uuid
from datetime import datetime
from typing import Optional
from app.core.database import get_session
from app.projects.models import Artifact


class ArtifactService:
    """Artifact 注册与管理"""

    def register_artifact(
        self,
        project_id: str,
        artifact_type: str,
        title: str,
        path: str,
        metadata: Optional[dict] = None,
    ) -> Artifact:
        db = get_session()
        try:
            artifact = Artifact(
                id=f"art_{uuid.uuid4().hex[:12]}",
                project_id=project_id,
                type=artifact_type,
                title=title,
                path=path,
                metadata_json=(metadata or {}),
                created_at=datetime.now().isoformat(),
            )
            db.add(artifact)
            db.commit()
            db.refresh(artifact)
            return artifact
        finally:
            db.close()

    def list_artifacts(self, project_id: str, artifact_type: Optional[str] = None) -> list[Artifact]:
        db = get_session()
        try:
            query = db.query(Artifact).filter(Artifact.project_id == project_id)
            if artifact_type:
                query = query.filter(Artifact.type == artifact_type)
            return query.order_by(Artifact.created_at.desc()).all()
        finally:
            db.close()

    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        db = get_session()
        try:
            return db.query(Artifact).filter(Artifact.id == artifact_id).first()
        finally:
            db.close()
