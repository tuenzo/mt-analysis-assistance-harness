## Overview

ArtifactService 是分析产物（图表、表格、模型输出、报告）的统一管理层。所有 pipeline（panel build、diagnostics、psm_did、localgap、gps、report）通过 ArtifactService 注册产物；前端通过 ArtifactService 读取产物 URL。

## Artifact 类型

```python
class ArtifactType(str, Enum):
    CHART = "chart"           # matplotlib/plotly 生成的趋势图、散点图
    TABLE = "table"           # pandas DataFrame 导出的 CSV/Excel
    MODEL_OUTPUT = "model_output"  # JSON 格式的模型结果（psm_did、localgap、gps）
    REPORT_SOURCE = "report_source"  # report.md 等报告源文件
    VALIDATION_REPORT = "validation_report"  # 数据质量报告
```

## Artifact 数据模型

```python
class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # uuid
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"))
    artifact_type: Mapped[ArtifactType]
    name: Mapped[str]  # 如 "gmv_trend", "localgap_total", "psm_did_result"
    version: Mapped[int] = mapped_column(Integer, default=1)
    file_path: Mapped[str]  # workspace 内相对路径，如 "artifacts/charts/gmv_trend.png"
    checksum: Mapped[str]  # SHA256
    tags: Mapped[list[str]]  # ["diagnostics", "gmv", "trend"]
    metadata_json: Mapped[dict]  # 灵活扩展：dimensions、metrics、生成时间等
    created_by_job_id: Mapped[str | None] = mapped_column(String, ForeignKey("jobs.id"))
    created_at: Mapped[datetime]

    # 多版本支持
    latest_version: Mapped[bool] = mapped_column(Boolean, default=True)
```

## ArtifactService 接口

```python
class ArtifactService:
    def register(
        self,
        project_id: str,
        artifact_type: ArtifactType,
        name: str,
        file_path: str,
        tags: list[str],
        metadata: dict,
        created_by_job_id: str | None = None,
    ) -> Artifact:
        """注册新 artifact，自动处理版本号"""

    def get(self, artifact_id: str) -> Artifact:
        """获取指定 artifact"""

    def get_latest(self, project_id: str, name: str) -> Artifact | None:
        """获取某 name 的最新版本"""

    def list_by_project(
        self,
        project_id: str,
        artifact_type: ArtifactType | None = None,
        tags: list[str] | None = None,
    ) -> list[Artifact]:
        """列出项目内 artifact，支持过滤"""

    def list_versions(self, project_id: str, name: str) -> list[Artifact]:
        """列出某 artifact 的所有版本"""

    def delete(self, artifact_id: str) -> None:
        """删除 artifact（软删除或硬删除）"""

    def compute_checksum(self, file_path: str) -> str:
        """计算文件 SHA256"""
```

## Artifacts API

```
GET  /api/projects/{project_id}/artifacts
     ?type=chart|table|model_output|report_source|validation_report
     &tags=gps,localgap
     → {ok, data: [artifact, ...]}

GET  /api/artifacts/{artifact_id}
     → {ok, data: artifact}

GET  /api/artifacts/{artifact_id}/download
     → 文件流

GET  /api/projects/{project_id}/artifacts/{name}/versions
     → {ok, data: [artifact_v1, artifact_v2, ...]}

DELETE /api/artifacts/{artifact_id}
     → {ok}
```

## 与 Pipeline 的集成

每个 pipeline 步骤完成后：

```python
# full_pipeline.py 示例
async def run_diagnostics(project_id: str):
    job = await JobOrchestrator.create_job(project_id, "diagnostics")

    result = await run_diagnostics_logic(project_id)

    chart_paths = render_diagnostics_charts(result)  # 返回 ["artifacts/charts/gmv_trend.png", ...]

    for path in chart_paths:
        ArtifactService.register(
            project_id=project_id,
            artifact_type=ArtifactType.CHART,
            name=Path(path).stem,
            file_path=path,
            tags=["diagnostics"],
            metadata={"chart_type": "trend"},
            created_by_job_id=job.id,
        )

    await JobOrchestrator.complete_job(job.id, {"status": "ok", ...})
```

## 与 Report 的集成

ReportRenderer 生成报告时，通过 ArtifactService 读取最新图表：

```python
class ReportRenderer:
    def render(self, project_id: str, result: LatestResult):
        # 获取最新版本的图表
        gmv_trend = ArtifactService.get_latest(project_id, "gmv_trend")
        localgap_chart = ArtifactService.get_latest(project_id, "localgap_total")
        gps_chart = ArtifactService.get_latest(project_id, "gps_dose_response")

        markdown = template.render(
            gmv_trend_url=gmv_trend.file_path,
            localgap_url=localgap_chart.file_path,
            gps_url=gps_chart.file_path,
        )

        # 注册报告为 artifact
        report_artifact = ArtifactService.register(
            project_id=project_id,
            artifact_type=ArtifactType.REPORT_SOURCE,
            name="analysis_report",
            file_path="reports/report.md",
            tags=["report"],
            metadata={"result_version": result.version},
        )

        return report_artifact
```

## 验收标准

1. pipeline 完成后 artifact 已注册到数据库
2. `GET /api/projects/{project_id}/artifacts?type=chart` 返回所有图表
3. `ArtifactService.get_latest(project_id, "gmv_trend")` 返回最新版
4. 同一 name 多次注册，version 递增，latest_version 正确指向最新
5. 报告生成时能通过 ArtifactService 获取图表路径
