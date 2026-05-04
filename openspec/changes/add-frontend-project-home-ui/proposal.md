## Why

Project Home 是用户进入项目后看到的第一个页面，需要展示项目状态、数据状态、最新结果、下一步建议。没有 Project Home，用户无法快速了解项目当前情况。根据 spec.md 第 160-162 行，Project Home 是 7 个核心页面之一。

## What Changes

- **新增** `ProjectHomePage` — 展示项目概览
- **新增** `ProjectStatusCard` — 当前阶段指示器（data_intake / analysis / report / memory）
- **新增** `DataStatusPanel` — 已上传文件列表 + 数据质量状态
- **新增** `LatestResultPanel` — 最新分析结果摘要
- **新增** `NextStepSuggestions` — 下一步建议（基于当前阶段）
- **新增** `QuickActions` — 快捷操作（上传数据、开始分析、生成报告）

## Capabilities

### New Capabilities
- `project-home-ui`: 项目首页

### Modified Capabilities
- `frontend-skeleton`: 扩展 project-store 的数据获取

## Impact

- **新建**: `frontend/src/features/project/project-home-page.tsx`
- **新建**: `frontend/src/features/project/project-status-card.tsx`
- **新建**: `frontend/src/features/project/data-status-panel.tsx`
- **新建**: `frontend/src/features/project/latest-result-panel.tsx`
- **新建**: `frontend/src/features/project/next-step-suggestions.tsx`
- **新建**: `frontend/src/features/project/quick-actions.tsx`
