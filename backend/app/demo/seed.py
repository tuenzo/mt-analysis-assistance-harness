import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from app.core.config import demo_reset_on_start, get_demo_project_id, is_demo_mode, settings
from app.core.database import get_session
from app.projects.models import (
    AgentEvent,
    AgentTurn,
    AnalysisSession,
    Artifact,
    ApprovalRequest,
    Project,
    ProjectFile,
    Report,
)
from app.workspace.context_summary import ContextSummaryWriter
from app.workspace.manager import WorkspaceManager
from app.workspace.manifest import AssetEntry, FileEntry, ProjectManifest, compute_file_checksum


DEMO_PROJECT_NAME = "Keemart 周期性促销评估 Demo"
DEMO_SESSION_ID = "demo_session_keemart"
FIXTURES_ROOT = Path(__file__).parent / "fixtures"


def seed_demo_if_enabled() -> dict | None:
    if not is_demo_mode():
        return None
    return DemoSeedService().seed(reset=demo_reset_on_start())


class DemoSeedService:
    def __init__(self):
        self.workspace_manager = WorkspaceManager(settings.workspace_root)

    def status(self) -> dict:
        project_id = get_demo_project_id()
        if not is_demo_mode():
            return {
                "enabled": False,
                "project_id": project_id,
                "project_name": DEMO_PROJECT_NAME,
                "session_id": None,
            }

        db = get_session()
        try:
            session = db.query(AnalysisSession).filter(AnalysisSession.project_id == project_id).first()
            return {
                "enabled": True,
                "project_id": project_id,
                "project_name": DEMO_PROJECT_NAME,
                "session_id": session.id if session else DEMO_SESSION_ID,
            }
        finally:
            db.close()

    def seed(self, reset: bool = True) -> dict:
        project_id = get_demo_project_id()
        db = get_session()
        try:
            existing = db.query(Project).filter(Project.id == project_id).first()
            if existing and reset:
                if not existing.is_test:
                    raise RuntimeError(f"Refusing to reset non-test project {project_id}")
                db.query(ApprovalRequest).filter(ApprovalRequest.project_id == project_id).delete()
                db.delete(existing)
                db.commit()
                workspace_path = self.workspace_manager.get_workspace_path(project_id)
                if workspace_path.exists():
                    root = (Path(settings.workspace_root) / "projects").resolve()
                    resolved = workspace_path.resolve()
                    if root not in resolved.parents and resolved != root:
                        raise RuntimeError(f"Refusing to delete workspace outside demo root: {workspace_path}")
                    shutil.rmtree(workspace_path)
            elif existing:
                session = db.query(AnalysisSession).filter(AnalysisSession.project_id == project_id).first()
                return {"project_id": project_id, "session_id": session.id if session else None}

            workspace_path = self.workspace_manager.create_workspace(project_id)
            now = datetime.now().isoformat()
            project = Project(
                id=project_id,
                name=DEMO_PROJECT_NAME,
                description="Repository-local demo project seeded for live product walkthroughs.",
                workspace_path=str(workspace_path),
                domain="promo_analysis",
                status="demo",
                current_stage="report_ready",
                is_test=1,
                created_at=now,
                updated_at=now,
            )
            db.add(project)
            db.flush()

            files = self._copy_fixtures_and_create_records(db, project, workspace_path, now)
            artifacts = self._create_artifacts(db, project_id, workspace_path, now)
            report = Report(
                id=f"rep_{uuid.uuid4().hex[:12]}",
                project_id=project_id,
                status="ready",
                title="Keemart Demo Business Analysis Report",
                source_md_path="reports/report.md",
                metadata_json=json.dumps({"demo": True}, ensure_ascii=False),
                created_at=now,
                updated_at=now,
            )
            db.add(report)

            session_id = self._seed_conversation(db, project_id, now)
            self._write_workspace_state(workspace_path, project_id, files, artifacts)
            db.commit()
            return {"project_id": project_id, "session_id": session_id}
        finally:
            db.close()

    def _copy_fixtures_and_create_records(self, db, project: Project, workspace_path: Path, now: str) -> list[ProjectFile]:
        mappings = [
            ("data/raw/order_info.csv", "order_info"),
            ("data/raw/exposure_info.csv", "exposure_info"),
            ("data/raw/activity_timeline.csv", "activity_timeline"),
            ("data/processed/category_date_panel.csv", "category_day_panel"),
        ]
        records = []
        for rel_path, role in mappings:
            source = FIXTURES_ROOT / rel_path
            target = workspace_path / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            record = ProjectFile(
                id=f"file_{uuid.uuid4().hex[:12]}",
                project_id=project.id,
                role=role,
                original_name=source.name,
                current_path=rel_path,
                size_bytes=target.stat().st_size,
                checksum=compute_file_checksum(target),
                status="validated" if role != "category_day_panel" else "generated",
                created_at=now,
                updated_at=now,
            )
            db.add(record)
            records.append(record)

        for source_rel, target_rel in [
            ("reports/business_analysis_report.md", "reports/report.md"),
            ("reports/technical_analysis_report.md", "reports/technical_analysis_report.md"),
        ]:
            source = FIXTURES_ROOT / source_rel
            target = workspace_path / target_rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

        return records

    def _create_artifacts(self, db, project_id: str, workspace_path: Path, now: str) -> list[Artifact]:
        artifacts = []
        for source_rel, target_rel, artifact_type, title, mime_type in [
            ("artifacts/tables/category_action_recommendations.csv", "artifacts/tables/category_action_recommendations.csv", "table", "Category action recommendations", "text/csv"),
            ("artifacts/charts/time_trends.png", "artifacts/charts/time_trends.png", "chart", "Demo time trends", "image/png"),
        ]:
            source = FIXTURES_ROOT / source_rel
            target = workspace_path / target_rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.exists():
                shutil.copy2(source, target)
            artifact = Artifact(
                id=f"art_{uuid.uuid4().hex[:12]}",
                project_id=project_id,
                type=artifact_type,
                title=title,
                path=target_rel,
                mime_type=mime_type,
                metadata_json=json.dumps({"demo": True}, ensure_ascii=False),
                checksum=compute_file_checksum(target),
                created_at=now,
            )
            db.add(artifact)
            artifacts.append(artifact)
        return artifacts

    def _seed_conversation(self, db, project_id: str, now: str) -> str:
        session = AnalysisSession(
            id=DEMO_SESSION_ID,
            project_id=project_id,
            runtime_provider="demo",
            external_session_id="demo_keemart_seed",
            status="active",
            created_at=now,
            updated_at=now,
        )
        db.add(session)

        turns = [
            (
                "demo_turn_data_ready",
                "这个项目现在数据准备好了吗？",
                "已准备好。演示项目已经加载 order_info.csv、exposure_info.csv、activity_timeline.csv，并生成 category_date_panel.csv、报告和图表 artifact。",
                [],
            ),
            (
                "demo_turn_increment",
                "促销是否真的带来增量？",
                "演示结论：活动期 GMV 和购买 UV 有抬升，但需要拆开发薪周期、曝光增长和折扣贡献。Drinks 建议加码曝光，Baby 建议控折扣优化，Rice/Oil 建议围绕发薪日前置。",
                [
                    {"type": "tool_call_started", "tool": "business_analysis", "action": "schema.infer", "payload": {}},
                    {"type": "tool_call_finished", "tool": "business_analysis", "action": "schema.infer", "ok": True, "summary": "识别三张核心数据表字段。"},
                    {"type": "tool_call_started", "tool": "business_analysis", "action": "panel.build_category_day", "payload": {}},
                    {"type": "tool_call_finished", "tool": "business_analysis", "action": "panel.build_category_day", "ok": True, "summary": "生成 category x day panel。"},
                    {"type": "tool_call_started", "tool": "business_analysis", "action": "analysis.run_full_pipeline", "payload": {}},
                    {"type": "tool_call_finished", "tool": "business_analysis", "action": "analysis.run_full_pipeline", "ok": True, "summary": "完成诊断、LocalGap 和策略建议。"},
                    {"type": "tool_call_started", "tool": "business_analysis", "action": "report.generate", "payload": {}},
                    {"type": "artifact_created", "artifact_id": "demo_report", "name": "Keemart Demo Business Analysis Report", "path": "reports/report.md"},
                    {"type": "tool_call_finished", "tool": "business_analysis", "action": "report.generate", "ok": True, "summary": "报告已生成。"},
                ],
            ),
        ]

        for turn_id, user_message, assistant_message, events in turns:
            turn = AgentTurn(
                id=turn_id,
                session_id=session.id,
                project_id=project_id,
                user_message=user_message,
                assistant_message=assistant_message,
                status="completed",
                created_at=now,
                completed_at=now,
            )
            db.add(turn)
            for event in events + [{"type": "final_answer", "message": assistant_message}]:
                payload = {**event, "turn_id": turn_id}
                db.add(AgentEvent(
                    id=f"evt_{uuid.uuid4().hex[:12]}",
                    session_id=session.id,
                    turn_id=turn_id,
                    project_id=project_id,
                    type=payload["type"],
                    payload_json=json.dumps(payload, ensure_ascii=False),
                    created_at=now,
                ))

        return session.id

    def _write_workspace_state(self, workspace_path: Path, project_id: str, files: list[ProjectFile], artifacts: list[Artifact]) -> None:
        latest_result = {
            "demo": True,
            "summary": "活动期 GMV 和购买 UV 抬升，建议按类目拆分曝光、折扣和发薪周期贡献。",
            "recommended_actions": [
                {"category": "drinks", "action": "scale_exposure"},
                {"category": "baby", "action": "optimize_discount"},
                {"category": "rice_oil", "action": "payday_timing"},
            ],
        }
        (workspace_path / ".analysis" / "latest_result.json").write_text(
            json.dumps(latest_result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        manifest = ProjectManifest.load(workspace_path)
        manifest.current_stage = "report_ready"
        manifest.files = [
            FileEntry(
                file_id=f.id,
                role=f.role,
                original_name=f.original_name,
                current_path=f.current_path,
                checksum=f.checksum,
                status=f.status,
                last_verified_at=f.updated_at,
            )
            for f in files
        ]
        manifest.derived_assets = [
            AssetEntry(
                asset_id=a.id,
                role=a.type,
                path=a.path,
                checksum=a.checksum,
                created_at=a.created_at,
            )
            for a in artifacts
        ]
        manifest.latest_result = latest_result
        manifest.version += 1
        manifest.save(workspace_path)

        ContextSummaryWriter(workspace_path).write(
            project_name=DEMO_PROJECT_NAME,
            current_stage="report_ready",
            file_status="\n".join(f"- {f.role}: {f.original_name} ({f.status})" for f in files),
            schema_status="demo mapped",
            completed_tasks="data_ingest, schema_infer, panel_build, diagnostics, report_generate",
            latest_artifact="reports/report.md; artifacts/charts/time_trends.png",
            conclusions="活动期 GMV 和购买 UV 抬升；Drinks 加码曝光，Baby 控折扣优化，Rice/Oil 发薪日前置。",
            pending_items="生产决策前需要完整样本、利润口径和实验验证。",
            next_steps="查看报告或继续通过 Agent 提问。",
        )
