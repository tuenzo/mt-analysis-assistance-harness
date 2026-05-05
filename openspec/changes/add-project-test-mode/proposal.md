## Why

Current local development can accumulate test projects in the normal project list, which makes the workspace noisy and risks mixing test fixtures with real analysis projects.

## What Changes

- Add an explicit backend test mode flag.
- Mark projects created while test mode is active as test projects.
- Hide test projects from normal project listing and loading paths unless test mode is enabled.
- Clean the existing local test project residue from the development database/workspaces.

## Impact

- Modified: `backend/app/core/config.py`
- Modified: `backend/app/core/database.py`
- Modified: `backend/app/projects/models.py`
- Modified: `backend/app/projects/schemas.py`
- Modified: `backend/app/projects/service.py`
- Modified: `backend/app/tests/test_projects_api.py`
- Modified: `.env.example`
