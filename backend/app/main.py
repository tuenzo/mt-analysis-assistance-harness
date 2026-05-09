from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import init_db
from app.api.projects import router as projects_router
from app.api.files import router as files_router
from app.api.agent_messages import router as agent_router
from app.api.sessions import router as sessions_router
from app.api.approvals import router as approvals_router
from app.api.reports import router as reports_router
from app.api.memory import router as memory_router
from app.api.demo import router as demo_router
from app.demo.seed import seed_demo_if_enabled

app = FastAPI(title="Business Analysis Companion Workspace")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
seed_demo_if_enabled()

app.include_router(projects_router, prefix="/api")
app.include_router(files_router, prefix="/api")
app.include_router(agent_router, prefix="/api")
app.include_router(sessions_router, prefix="/api")
app.include_router(approvals_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(memory_router, prefix="/api")
app.include_router(demo_router, prefix="/api")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/projects")
def list_projects():
    from app.projects.service import ProjectService
    service = ProjectService()
    projects = service.list_projects()
    return {"ok": True, "data": [{"id": p.id, "name": p.name, "status": p.status, "created_at": p.created_at} for p in projects]}


@app.get("/api/projects/{project_id}/sessions")
def list_project_sessions(project_id: str):
    from app.agent.session_store import SessionStore
    store = SessionStore()
    sessions = store.list_project_sessions(project_id)
    return {
        "ok": True,
        "data": [
            {
                "id": s.id,
                "project_id": s.project_id,
                "runtime_provider": s.runtime_provider,
                "status": s.status,
                "created_at": s.created_at,
            }
            for s in sessions
        ]
    }
