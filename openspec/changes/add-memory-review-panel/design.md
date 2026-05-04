## Overview

Memory Review Panel 的后端 API 支持前端展示记忆候选列表，并处理用户的确认/拒绝操作。approve 后同步到项目内记忆或导出供用户手动同步到全局记忆。

## MemoryCandidate 数据模型

```python
class MemoryScope(str, Enum):
    PROJECT = "project"  # 当前项目内有用结论
    USER_PREFERENCE = "user_preference"  # 用户分析方法偏好
    GLOBAL_BUSINESS_MEMORY = "global_business_memory"  # 跨项目复用业务结论

class MemoryCategory(str, Enum):
    CONCLUSION = "conclusion"  # 分析结论（如 "LocalGap 中 discount 占 60%"）
    PREFERENCE = "preference"  # 方法偏好（如 "倾向先跑 diagnostics"）
    METHODOLOGY = "methodology"  # 方法论（如 "payday promotion 效果通常优于非 payday"）
    DATA_CALIBRATION = "data_calibration"  # 数据口径（如 "gmv 定义为实付金额"）

class MemoryCandidate(Base):
    __tablename__ = "memory_candidates"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"))
    scope: Mapped[MemoryScope]
    category: Mapped[MemoryCategory]
    content: Mapped[str]  # 记忆内容文本
    source_artifact_ids: Mapped[list[str]] = mapped_column(JSON, default=list)  # 关联 artifact
    status: Mapped[str] = mapped_column(String, default="pending")  # pending/approved/rejected
    approved_at: Mapped[datetime | None]
    rejected_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

## MemoryCandidates API

```
GET  /api/projects/{project_id}/memory/candidates
     ?scope=project|user_preference|global_business_memory
     &status=pending|approved|rejected
     → {ok, data: [candidate, ...]}

GET  /api/memory/candidates/{id}
     → {ok, data: candidate}

POST /api/memory/candidates/{id}/approve
     body: {sync_target: "project"|"export"}
     → {ok, data: {candidate, sync_result}}

POST /api/memory/candidates/{id}/reject
     → {ok, data: {candidate}}

POST /api/projects/{project_id}/memory/generate-candidates
     # 手动触发从 latest_result 生成候选（通常是 pipeline 完成后自动触发）
     → {ok, data: {count: 5}}
```

## MemorySyncService

```python
class MemorySyncService:
    def sync_to_project_memory(self, candidate: MemoryCandidate) -> str:
        """写入 .analysis/memory_candidates.md"""
        path = workspace / ".analysis" / "memory_candidates.md"
        append_to_file(path, candidate.to_markdown())
        return path

    def export_for_global_memory(self, candidate: MemoryCandidate) -> str:
        """导出到 .analysis/global_memory_export.md，供用户手动同步"""
        path = workspace / ".analysis" / "global_memory_export.md"
        append_to_file(path, candidate.to_markdown())
        return path

    def get_project_memory(self, project_id: str) -> list[MemoryCandidate]:
        """读取项目内所有 approved 记忆"""
        return self.db.query(MemoryCandidate).filter(
            project_id=project_id,
            scope=MemoryScope.PROJECT,
            status="approved"
        ).all()
```

## 记忆候选生成策略

Pipeline 完成后自动生成候选（也可手动触发）：

```python
async def generate_memory_candidates(project_id: str, result: LatestResult):
    candidates = []

    # 1. 项目摘要（project scope, conclusion）
    candidates.append(MemoryCandidate(
        project_id=project_id,
        scope=MemoryScope.PROJECT,
        category=MemoryCategory.CONCLUSION,
        content=f"本期 {result.project_name} 分析完成。"
               f"GMV 变化 {result.gmv_change_pct}%，"
               f"LocalGap 总增量 {result.localgap_total}，"
               f"Persuadables 占比 {result.gps_persuadables_pct}%。",
        source_artifact_ids=[result.artifact_id],
    ))

    # 2. 策略模式（global_business_memory, methodology）
    for strategy in result.gps.strategies:
        if strategy.type == "Persuadables":
            candidates.append(MemoryCandidate(
                project_id=project_id,
                scope=MemoryScope.GLOBAL_BUSINESS_MEMORY,
                category=MemoryCategory.METHODOLOGY,
                content=f"Persuadables 品类（{strategy.category}）"
                       f"在 discount={strategy.avg_discount}% 时效果最优，"
                       f"建议重点投入。",
                source_artifact_ids=[result.gps_artifact_id],
            ))

    # 3. 方法偏好（user_preference）— 需要基于历史行为推断，此处先做占位
    # 实际实现可能需要分析用户历史选择

    for c in candidates:
        db.add(c)
    db.commit()
```

## 记忆内容约束（MemoryCandidate.content）

**允许写入**：
- 分析结论（数字、变化百分比）
- 数据口径说明
- 方法偏好
- 策略模式

**禁止写入**：
- 原始数据（订单明细、用户 ID）
- 中间假设
- 错误结论
- 敏感信息

## 与前端的交互

前端 Memory Review Panel 调用 MemoryCandidates API：
1. `GET /api/projects/{project_id}/memory/candidates?status=pending` 获取待确认列表
2. 展示每个 candidate 的 content、scope、category、source
3. 用户点击 approve → `POST /api/memory/candidates/{id}/approve`
4. 用户点击 reject → `POST /api/memory/candidates/{id}/reject`
5. 刷新列表

## 验收标准

1. `GET /api/projects/{project_id}/memory/candidates` 返回候选列表
2. `POST /api/memory/candidates/{id}/approve` 后 status=approved，写入 .analysis/memory_candidates.md
3. `POST /api/memory/candidates/{id}/reject` 后 status=rejected
4. pipeline 完成后自动生成候选
5. 候选内容符合约束（无原始数据）
