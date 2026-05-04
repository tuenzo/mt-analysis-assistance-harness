from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.projects.service import ProjectService
from app.tools.memory_tools import memory_generate_summary, memory_get, memory_approve
from app.core.database import get_session
from app.projects.models import MemoryCandidate

router = APIRouter(prefix="/projects", tags=["memory"])


@router.get("/{project_id}/memory/candidates")
def list_memory_candidates(project_id: str):
    db = get_session()
    try:
        candidates = db.query(MemoryCandidate).filter(
            MemoryCandidate.project_id == project_id
        ).order_by(MemoryCandidate.created_at.desc()).all()
        return {
            "ok": True,
            "data": [
                {
                    "id": c.id,
                    "scope": c.scope,
                    "content": c.content,
                    "status": c.status,
                    "created_at": c.created_at,
                }
                for c in candidates
            ]
        }
    finally:
        db.close()


@router.get("/{project_id}/memory")
def get_project_memory(project_id: str, scope: str = "project"):
    result = memory_get(project_id, {"scope": scope})
    if not result.ok:
        raise HTTPException(status_code=400, detail=result.error)
    return {"ok": True, "data": result.artifacts}


@router.post("/{project_id}/memory/summary")
def generate_memory_summary(project_id: str):
    result = memory_generate_summary(project_id, {})
    if not result.ok:
        raise HTTPException(status_code=400, detail=result.error)
    return {"ok": True, "result": result.model_dump()}


@router.post("/memory/candidates/{candidate_id}/approve")
def approve_memory_candidate(candidate_id: str):
    db = get_session()
    try:
        candidate = db.query(MemoryCandidate).filter(MemoryCandidate.id == candidate_id).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        candidate.status = "approved"
        db.commit()

        result = memory_approve(
            candidate.project_id,
            candidate.id,
            candidate.content,
            candidate.scope,
        )

        return {"ok": True, "result": result.model_dump()}
    finally:
        db.close()


@router.post("/memory/candidates/{candidate_id}/reject")
def reject_memory_candidate(candidate_id: str):
    db = get_session()
    try:
        candidate = db.query(MemoryCandidate).filter(MemoryCandidate.id == candidate_id).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        candidate.status = "rejected"
        db.commit()

        return {"ok": True, "data": {"status": "rejected"}}
    finally:
        db.close()
