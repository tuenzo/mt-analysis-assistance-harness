# Business Analysis Companion Workspace

Local-first business analysis harness with a FastAPI backend, Next.js frontend,
SQLite project state, workspace-backed artifacts, and a single
`business_analysis` tool gateway for agent-driven analysis.

## Current Development Environment

Confirmed on 2026-05-12 for the current agent-flow validation stage:

- `setup.ps1`, `setup.sh`, and `scripts/local_setup.py` are not verified yet.
  Do not use them as the acceptance path until they receive a separate
  validation pass.
- Before starting services, stop stale backend/frontend processes from this
  repository. Historical runs have used ports `8000`, `8010`, `8017`, `8025`,
  `18080`, `18081`, `18191`-`18194`, `3010`, `3025`, and `4180`.
- Backend URL: `http://127.0.0.1:18081`
- Frontend URL: `http://127.0.0.1:3010`
- Runtime check: `GET http://127.0.0.1:18081/api/agent/runtime`
- Current validation project: `Keemart 促销增长全流程项目`

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 18081
```

Frontend:

```powershell
cd frontend
$env:NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:18081'
npm run dev -- -H 127.0.0.1 -p 3010
```

## Documentation Maintenance

Whenever the development environment, service ports, startup procedure,
validation project, or setup-script status changes and is persisted to disk, the
agent must check and update both `AGENTS.md` and this `README.md` in the same
work session. If setup-script status changes, also check `SETUP.md`.
