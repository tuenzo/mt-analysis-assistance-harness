## Overview

本变更实现分析 pipeline 的核心逻辑。AnalysisToolGateway 调用内部工具，内部工具执行真实分析任务。这些 pipeline 是系统商业价值的核心。

## 目录结构

```
backend/app/analysis/pipelines/
├── build_panel.py      # 品类×日期面板构建
├── diagnostics.py      # 描述性诊断
├── psm_did.py          # PSM-DID 因果推断
├── localgap.py         # LocalGap 增量分解
├── gps_uplift.py       # GPS-Uplift 剂量响应
└── full_pipeline.py    # 完整 pipeline 编排
```

## 数据流

```
order_info.csv ─────┐
exposure_info.csv ──┼─→ build_panel.py ──→ category_day_panel.parquet
activity_timeline ──┘                              │
                                                  ▼
                            ┌─ diagnostics.py ──→ trend.png
                            │
category_day_panel ─────────┼─ psm_did.py ──→ psm_did_result.json
                            │
                            ├─ localgap.py ──→ localgap_total.png + result.json
                            │
                            └─ gps_uplift.py ──→ gps_dose_response.png + uplift_result.json
                                                  │
                                                  ▼
                              latest_result.json ──→ chart.render ──→ artifacts/charts/
                                                  │
                                                  └─→ report.generate ──→ report.md
```

## Panel Build

输入：三张表（order_info, exposure_info, activity_timeline）
输出：`data/processed/category_day_panel.parquet`

字段：
- date, category
- gmv, discount, discount_rate
- exposure, exposure_rate
- order_count, user_count
- is_payday, is_activity, is_payday_activity

关键逻辑：
- 日期对齐（所有表按 date 合并）
- 品类聚合（order 按 category 聚合）
- 活动标记（activity_timeline 标记活动期）
- 发薪日标记（基于 activity_timeline 的 payday 字段）

## Diagnostics

输入：category_day_panel.parquet
输出：
- GMV trend（时间序列）
- activity vs non-activity 对比
- payday overlap 分析
- category concentration top10

## PSM-DID

输入：category_day_panel.parquet
输出：
- PSM propensity model（基于 exposure probability）
- DID estimate + confidence interval
- parallel trend test result
- placebo test result

## LocalGap

输入：category_day_panel.parquet
输出：
- LocalBaseline（无活动期反事实）
- LocalGap = actual - baseline
- 分解：exposure_gap, discount_gap, payday_gap, interaction, residual
- category × gap 矩阵

## GPS-Uplift

输入：category_day_panel.parquet
输出：
- GPS propensity（Generalized Propensity Score）
- exposure response function
- discount response function
- heterogeneity by category tier and payday window
- Persuadables / Sure Things / Lost Causes / Do Not Disturb 分类

## Full Pipeline

顺序执行：
1. data.validate（检查三张表）
2. panel.build_category_day
3. analysis.run_diagnostics
4. analysis.run_localgap
5. analysis.run_gps_uplift
6. chart.render（生成关键图表）
7. result.get_latest（更新 latest_result.json）

每个步骤：
- 创建 Job（status: queued → running → succeeded/failed）
- 发送 job_started / job_progress / job_finished 事件
- 产出 artifact 并注册到 ArtifactService
- 更新 project_manifest.latest_result

## Job Orchestrator

```python
class JobOrchestrator:
    def run_pipeline(self, project_id: str, pipeline_name: str, **kwargs) -> AsyncIterator[dict]:
        # 异步生成器，每个 step yield 进度
        # 内部使用 asyncio 或 thread pool
```

## Stub vs Real

MVP 阶段：
- `analysis.run_gps_uplift` 可以是 stub（只生成占位 result + method_status="stub"）
- `analysis.run_psm_did` 如果太复杂可先做简化版

但 `data.validate`、`panel.build_category_day`、`analysis.run_localgap` 必须实现真实逻辑。