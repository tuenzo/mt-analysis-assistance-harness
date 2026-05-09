## Why

项目管理页只能创建和进入项目，无法删除不再需要的分析项目。MVP 骨架验证阶段会频繁创建测试项目，如果没有删除入口，项目列表会快速变得杂乱，workspace 和数据库记录也无法从 UI 清理。

## What Changes

- 新增后端 `DELETE /api/projects/{project_id}`，删除项目数据库记录与项目 workspace。
- 项目列表页为每个项目增加删除按钮。
- 删除前弹出确认弹窗，明确提示会删除项目 workspace 与相关记录。
- 前端删除成功后刷新项目列表并清理当前项目状态。

## Impact

- 修改 `backend/app/projects/service.py`
- 修改 `backend/app/api/projects.py`
- 修改 `backend/app/tests/test_projects_api.py`
- 修改 `frontend/src/lib/api-client.ts`
- 修改 `frontend/src/store/project-store.ts`
- 修改 `frontend/src/app/projects/page.tsx`
