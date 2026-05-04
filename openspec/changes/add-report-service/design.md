## Overview

ReportService 负责将分析结果（latest_result.json）渲染为结构化 Markdown 报告，并支持导出为 PDF。

## Report 数据模型

```python
class ReportType(str, Enum):
    PROMO_ANALYSIS = "promo_analysis"  # 促销分析报告（默认模板）
    EXECUTIVE_SUMMARY = "executive_summary"  # 执行摘要

class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"))
    report_type: Mapped[ReportType]
    template_name: Mapped[str] = mapped_column(String, default="promo_analysis_default")
    title: Mapped[str]
    content_md: Mapped[str]  # 渲染后的 markdown
    file_path: Mapped[str]  # reports/{report_id}.md
    exported_path: Mapped[str | None]  # reports/{report_id}.pdf
    metadata_json: Mapped[dict]  # date_range, category_count 等
    created_by_job_id: Mapped[str | None] = mapped_column(String, ForeignKey("jobs.id"))
    created_at: Mapped[datetime]
```

## ReportRenderer

```python
class ReportRenderer:
    def __init__(self, template_name: str = "promo_analysis_default"):
        self.template = self._load_template(template_name)

    def render(self, project_id: str, result: LatestResult) -> str:
        """
        读取 latest_result.json、context_summary、各 pipeline 结果，
        填充 template，返回 rendered markdown
        """
```

### Template 填充字段

| 占位符 | 数据来源 | 示例 |
|--------|---------|------|
| `{project_name}` | project_manifest | "Keemart 端午节促销" |
| `{date_range}` | latest_result.metadata | "2024-06-01 ~ 2024-06-30" |
| `{order_count}` | latest_result.data_summary.order_count | "1,234,567" |
| `{category_count}` | latest_result.data_summary.category_count | "128" |
| `{trend_summary}` | diagnostics_result.gmv_trend | "活动期 GMV 提升 23%" |
| `{localgap_total}` | localgap_result.total | "+¥1.2M" |
| `{gps_persuadables}` | gps_result.persuadables_pct | "15.3%" |
| `{strategy_matrix}` | gps_result.strategy_table | markdown table |
| `{chart_refs}` | ArtifactService | ![img](artifacts/charts/...) |

## Export 流程

```
report.md
   │
   ▼
Exporter.to_pdf(markdown_path, output_path)
   │
   ├─ markdown → pdf 转换（使用 markdown + weasyprint 或 pandoc）
   │
   ▼
reports/{report_id}.pdf
```

第一版使用 `markdown + weasyprint`（Python 原生），后续可扩展 LaTeX。

## Reports API

```
POST /api/projects/{project_id}/reports/generate
     body: {report_type: "promo_analysis", template_name: "promo_analysis_default"}
     → {ok, data: {report_id, content_md, file_path}}

GET  /api/projects/{project_id}/reports
     → {ok, data: [report, ...]}

GET  /api/projects/{project_id}/reports/latest
     → {ok, data: report}

GET  /api/reports/{report_id}
     → {ok, data: report}

POST /api/reports/{report_id}/export
     body: {format: "pdf"}
     → {ok, data: {exported_path}}

GET  /api/reports/{report_id}/download
     → 文件流（md 或 pdf）
```

## 与 Pipeline 的集成

```python
# full_pipeline.py 末尾
async def run_full_pipeline(project_id: str):
    result = await _run_all_steps(project_id)

    # 生成报告
    report = await ReportService.generate(
        project_id=project_id,
        report_type=ReportType.PROMO_ANALYSIS,
        result=result,
    )

    return report
```

## 报告模板结构 (promo_analysis_default)

```markdown
# {project_name} 商业分析报告

## 摘要
<!-- 3-5 句话核心结论：GMV 变化、增量来源、策略建议 -->

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
![增量分解]({localgap_chart_path})

### 剂量响应
<!-- 引用 gps_dose_response.png -->
![剂量响应]({gps_chart_path})

### 策略分层
{strategy_matrix}

## 策略建议
<!-- 基于 uplift ranking 的 actionable 建议 -->

## 限制说明
- 样本量限制
- 因果识别假设
- 数据质量限制

## 下周期建议
<!-- 基于本周期分析的下一步 -->
```

## 验收标准

1. `POST /api/projects/{project_id}/reports/generate` 生成真实报告内容
2. 报告包含摘要、数据说明、方法、核心结果、策略建议、限制、下周期建议
3. 报告引用了 ArtifactService 中的图表
4. `POST /api/reports/{report_id}/export` 生成 PDF 文件
5. `GET /api/projects/{project_id}/reports/latest` 返回最新报告
