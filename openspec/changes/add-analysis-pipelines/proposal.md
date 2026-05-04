## Why

分析 pipeline 是系统的核心价值。从 panel build 到 LocalGap 到 GPS-Uplift，这些才是真正产出商业洞察的步骤。没有这些 pipeline，系统只是个空壳工作区，无法回答"活动是否有效、增量来自哪里、资源应投给谁"。

## What Changes

- **新增** `data.validate` — 检查 order_info/exposure_info/activity_timeline 存在性、日期字段、品类字段、缺失率、重复行
- **新增** `panel.build_category_day` — 生成 category_day_panel.parquet（category × day × GMV/discount/exposure/order/user）
- **新增** `analysis.run_diagnostics` — GMV trend、活动期/非活动期对比、payday overlap、品类集中度
- **新增** `analysis.run_psm_did` — PSM 模型 + DID 估计、parallel trend 检验、placebo check
- **新增** `analysis.run_localgap` — LocalBaseline / LocalGap 增量分解（exposure/discount/payday/interaction/residual）
- **新增** `analysis.run_gps_uplift` — GPS 剂量响应（exposure response、discount response、heterogeneity by tier/window）
- **新增** `analysis.run_full_pipeline` — 顺序执行 data.validate → panel → diagnostics → localgap → gps → strategy
- **新增** `result.get_latest` — 读取 latest_result.json
- **新增** `chart.render` — 基于 result 生成可视化图表（matplotlib/plotly）
- **新增** `ArtifactService` 注册图表/表格/model_output 为 artifact

## Capabilities

### New Capabilities
- `analysis-pipelines`: 数据校验、面板构建、因果推断、增量分解、剂量响应完整链路
- `result-visualization`: 分析结果图表化

### Modified Capabilities
- 无

## Impact

- **新建**: `backend/app/analysis/pipelines/build_panel.py`
- **新建**: `backend/app/analysis/pipelines/diagnostics.py`
- **新建**: `backend/app/analysis/pipelines/psm_did.py`
- **新建**: `backend/app/analysis/pipelines/localgap.py`
- **新建**: `backend/app/analysis/pipelines/gps_uplift.py`
- **新建**: `backend/app/analysis/pipelines/full_pipeline.py`
- **新建**: `backend/app/jobs/orchestrator.py` — 长任务编排
- **新建**: `backend/app/jobs/runner.py` — JobRunner
- **新建**: `backend/app/jobs/queue.py` — JobQueue
- **新建**: `backend/app/artifacts/service.py` — ArtifactService
- **修改**: `backend/app/tools/analysis_tools.py` — 接入上述 pipeline
- **测试**: 各 pipeline 单元测试、端到端 full_pipeline 测试