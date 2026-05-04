## Tasks

### Phase 0: 环境与配置

- [x] **T0.1** — 创建 `backend/` 目录结构
  ```
  backend/
    app/
      __init__.py
      main.py
      core/
        __init__.py
        config.py
      workspace/
        __init__.py
        manager.py
        manifest.py
        context_summary.py
        scanner.py
        checksums.py
        checkpoints.py
  ```
- [x] **T0.2** — 在 `config.py` 中添加 workspace 配置项
  ```python
  class Settings(BaseSettings):
      workspace_root: Path = Path("./workspaces")
      workspace_version: int = 1
  ```
- [x] **T0.3** — 创建 `requirements.txt`（fastapi, uvicorn, sqlalchemy, pydantic 等）

### Phase 1: Workspace 目录结构

- [x] **T1.1** — 定义 workspace 目录模板常量
  ```python
  WORKSPACE_TEMPLATE = {
      "data/raw": [],
      "data/processed": [],
      "scripts": [],
      "artifacts/charts": [],
      "artifacts/tables": [],
      "artifacts/model_outputs": [],
      "reports": [],
      "logs": [],
      ".analysis": [],
      ".claude": []
  }
  ```
- [x] **T1.2** — 实现 `WorkspaceManager.create_workspace(project_id) → Path`
  - 在 `workspace_root` 下创建 `projects/{project_id}/` 目录结构
  - 初始化所有子目录
  - 返回 workspace 路径
- [x] **T1.3** — 实现 `WorkspaceManager.get_workspace_path(project_id) → Path`

### Phase 2: Manifest 管理

- [x] **T2.1** — 定义 `ProjectManifest` dataclass
  ```python
  @dataclass
  class ProjectManifest:
      project_id: str
      version: int
      current_stage: str
      files: list[FileEntry]
      derived_assets: list[AssetEntry]
      latest_result: dict | None
  ```
- [x] **T2.2** — 实现 `ProjectManifest.load(project_id) → ProjectManifest`
- [x] **T2.3** — 实现 `ProjectManifest.save(project_id, manifest)`
- [x] **T2.4** — 实现 `WorkspaceManager.update_project_manifest(project_id)`
- [x] **T2.5** — 实现 `WorkspaceManager.scan_workspace(project_id) → list[FileEntry]`
  - 扫描 data/raw、data/processed 等目录
  - 计算 checksum
  - 对比 manifest 检测 stale 文件

### Phase 3: Context Summary

- [x] **T3.1** — 定义 context_summary.md 模板格式
  ```markdown
  # 项目: {name}
  ## 当前阶段: {current_stage}
  ## 数据文件状态
  ## 字段映射状态
  ## 已完成任务
  ## 最新 artifact
  ## 核心结论
  ## 待确认事项
  ## 下一步建议
  ```
- [x] **T3.2** — 实现 `write_context_summary(project_id, data)`
- [x] **T3.3** — 实现 `read_context_summary(project_id) → str`

### Phase 4: CLAUDE.md 模板

- [x] **T4.1** — 创建 `.claude/CLAUDE.md` 模板文件内容
  ```markdown
  你正在 Business Analysis Companion Workspace 中工作。
  不要臆造数据结果。
  需要真实数据、图表、模型、报告时，调用 business_analysis 工具。
  当前项目状态以 .analysis/context_summary.md 和 project_manifest.json 为准。
  ```
- [x] **T4.2** — `WorkspaceManager.init_claude_context(project_id)` — 在新 workspace 创建时自动写入

### Phase 5: Checkpoints

- [x] **T5.1** — 实现 `WorkspaceManager.create_checkpoint(project_id, label)`
  - 快照 manifest 状态到 `.analysis/checkpoints/{timestamp}_{label}.json`
- [x] **T5.2** — 实现 `WorkspaceManager.list_checkpoints(project_id) → list[CheckpointInfo]`
- [x] **T5.3** — 实现 `WorkspaceManager.restore_checkpoint(project_id, checkpoint_id)`

### Phase 6: 验证测试

- [x] **T6.1** — 编写测试：`test_workspace_manager.py`
  - 创建 workspace 后目录结构正确
  - manifest 初始化正确
  - scan 检测到正确文件数量
  - context_summary 读写正常
  - checkpoint 创建/恢复正常
- [x] **T6.2** — 运行测试，修复问题

---

## 验收标准

1. 调用 `WorkspaceManager.create_workspace("proj_001")` 后，目录结构符合模板
2. `.analysis/project_manifest.json` 存在且格式正确
3. `.analysis/context_summary.md` 存在且包含项目基本信息
4. `.claude/CLAUDE.md` 存在且包含基本 agent 指令
5. checksum 计算正确
6. checkpoint 创建后可恢复
7. 所有测试通过