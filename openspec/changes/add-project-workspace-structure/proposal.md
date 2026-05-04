## Why

MVP 0 阶段需要先建立 workspace 目录结构作为项目事实源。没有 workspace 就没有地方存放数据、脚本、artifacts、reports，也就没有办法验证后续 message runtime、tool gateway 和 analysis pipeline 的正确性。当前项目是空骨架，无法跑通基本流程。

## What Changes

- **新增** workspace 目录结构模板（`workspaces/{project_id}/` 及其子目录）
- **新增** `.analysis/project_manifest.json` — 文件事实状态管理
- **新增** `.analysis/context_summary.md` — 项目状态摘要（供 Claude 读取）
- **新增** `.analysis/latest_result.json` — 最新分析结果占位
- **新增** `.analysis/artifact_manifest.json` — artifact 注册表
- **新增** `.analysis/memory_candidates.md` — 项目内记忆候选
- **新增** `.analysis/checkpoints/` — workspace 快照目录
- **新增** `.claude/CLAUDE.md` — Claude agent 上下文指令
- **新增** `logs/` 目录（含 `agent_events.jsonl`、`tool_calls.jsonl`、`jobs.jsonl`、`errors.jsonl`）
- **新增** `WorkspaceManager` — 创建 workspace、验证目录结构、管理 manifest

## Capabilities

### New Capabilities
- `project-workspace-structure`: 定义 workspace 目录布局、manifest 格式、context_summary 模板、CLAUDE.md 指令格式

### Modified Capabilities
- 无（首个变更，无历史依赖）

## Impact

- **新建**: `backend/app/workspace/manager.py` — WorkspaceManager 类
- **新建**: `backend/app/workspace/manifest.py` — project_manifest.json 读写
- **新建**: `backend/app/workspace/context_summary.py` — context_summary.md 生成
- **新建**: `backend/app/core/config.py` — workspace_root 等配置
- **测试**: workspace 创建、manifest 读写、context 生成