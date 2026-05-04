## Overview

本变更实现报告生成与记忆桥接系统。报告让分析结果变成可分享的交付物；记忆桥接让系统成为真正的"伴随式个人助手"。

## Report 生成流程

```
latest_result.json
      │
      ▼
ReportRenderer.generate()
      │
      ├─ 读取 project_manifest.json
      ├─ 读取 diagnostics_result.json
      ├─ 读取 localgap_result.json
      ├─ 读取 gps_result.json
      ├─ 渲染 markdown 模板
      │
      ▼
reports/report.md + artifact(type=report_source)
```

## Report 模板结构 (promo_analysis_default)

```markdown
# {project_name} 商业分析报告

## 摘要
<!-- 3-5 句话核心结论，GMV 变化、增量来源、策略建议 -->

## 数据说明
### 数据时间范围
{date_range}

### 数据覆盖
- 订单表：{order_count} 条，{category_count} 个品类
- 曝光表：{exposure_count} 条
- 活动表：{activity_count} 个活动

### 字段映射
{schema_mapping_table}

## 分析方法
1. 数据校验 → 面板构建
2. 描述性诊断（GMV 趋势、活动效果）
3. 因果推断（PSM-DID）
4. 增量分解（LocalGap）
5. 剂量响应（GPS-Uplift）

## 核心结果

### GMV 概览
{trend_summary}

### 增量分解
<!-- 引用 localgap_total.png -->
![增量分解](artifacts/charts/localgap_total.png)

### 剂量响应
<!-- 引用 gps_dose_response.png -->
![剂量响应](artifacts/charts/gps_dose_response.png)

### 策略分层
| 类型 | 占比 | 建议 |
|------|------|------|
| Persuadables | 15% | 重点投入 |
| ... | ... | ... |

## 策略建议
<!-- 基于 uplift ranking 的 actionable 建议 -->

## 限制说明
- 样本量限制
- 因果识别假设
- 数据质量限制

## 下周期建议
<!-- 基于本周期分析的下一步 -->
```

## Memory Bridge 设计

```
Analysis 完成
    │
    ▼
MemoryBridge.propose_update(project_id, content, scope, source_artifact_ids)
    │
    ├─ 生成 MemoryCandidate record (status=pending)
    ├─ 内容：项目摘要 / 用户偏好 / 业务结论（不包含原始数据）
    │
    ▼
用户在 Memory Review Panel 查看
    │
    ├─ approve(scope=project) → 写入 .analysis/memory_candidates.md
    ├─ approve(scope=user_preference) → 写入 .analysis/preferences.md
    ├─ approve(scope=global) → 写入 .analysis/global_memory_export.md
    │     （不直接写 ~/.claude）
    └─ reject → 保持 pending
```

## Scope 说明

- `project` — 当前项目内有用结论，供后续分析参考
- `user_preference` — 用户分析方法偏好（如"倾向先跑 diagnostics"）
- `global_business_memory` — 跨项目复用业务结论（如"payday promotion 效果通常优于非 payday"）

## MemoryCandidate 内容约束

**允许写入**：
- 分析结论（"LocalGap 中 discount 占 60%"）
- 数据口径说明（"gmv 定义为实付金额"）
- 方法偏好（"优先 GPS 而非 PSM-DID"）
- 策略模式（"活动期 discount 超过 15% 时效果递减"）

**禁止写入**：
- 原始数据（订单明细、用户 ID）
- 中间假设
- 错误结论
- 敏感信息

## 全局记忆写入边界

配置项：`allow_global_memory_write: bool`（默认 False）

当 `allow_global_memory_write=True` 且 `scope=global_business_memory` 时，可写入用户级 Claude memory。

否则只写入 `.analysis/global_memory_export.md`，由用户手动同步。