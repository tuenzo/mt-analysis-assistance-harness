from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import init_db
from app.api.projects import router as projects_router
from app.api.files import router as files_router

app = FastAPI(title="Business Analysis Companion Workspace")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

app.include_router(projects_router, prefix="/api")
app.include_router(files_router, prefix="/api")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/projects")
def list_projects():
    from app.projects.service import ProjectService
    service = ProjectService()
    projects = service.list_projects()
    return {"ok": True, "data": [{"id": p.id, "name": p.name, "status": p.status, "created_at": p.created_at} for p in projects]}
