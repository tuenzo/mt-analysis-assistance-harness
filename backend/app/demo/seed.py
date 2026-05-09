import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from app.core.config import demo_reset_on_start, get_demo_project_id, is_demo_mode, resolve_project_path, settings
from app.analysis.dashboard_chart_renderer import DEFAULT_DASHBOARD_CHART_IDS, render_dashboard_chart
from app.core.database import get_session
from app.projects.models import (
    AgentEvent,
    AgentTurn,
    AnalysisSession,
    ApprovalRequest,
    Artifact,
    Job,
    MemoryCandidate,
    Project,
    ProjectFile,
    Report,
    ToolCall,
)
from app.workspace.context_summary import ContextSummaryWriter
from app.workspace.manager import WorkspaceManager
from app.workspace.manifest import AssetEntry, FileEntry, ProjectManifest, compute_file_checksum


DEMO_PROJECT_NAME = "Keemart 促销增长全流程演示 Demo"
DEMO_SESSION_ID = "demo_session_keemart_full"
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
            session = (
                db.query(AnalysisSession)
                .filter(
                    AnalysisSession.project_id == project_id,
                    AnalysisSession.runtime_provider != "demo",
                )
                .order_by(AnalysisSession.updated_at.desc(), AnalysisSession.created_at.desc())
                .first()
            )
            return {
                "enabled": True,
                "project_id": project_id,
                "project_name": DEMO_PROJECT_NAME,
                "session_id": session.id if session else None,
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
                db.query(AgentEvent).filter(AgentEvent.project_id == project_id).delete()
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
                session_id = self._ensure_existing_demo_ready(db, existing)
                db.commit()
                return {"project_id": project_id, "session_id": session_id}

            workspace_path = self.workspace_manager.create_workspace(project_id).resolve()
            now = datetime.now().isoformat()
            project = Project(
                id=project_id,
                name=DEMO_PROJECT_NAME,
                description="功能齐全的本地演示项目：数据接入、Agent 审批、Pipeline、Timeline、Dashboard、Reports、Memory 全部可看。",
                workspace_path=str(workspace_path),
                domain="promo_analysis",
                status="report_ready",
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
                title="Keemart 促销增长全流程演示报告",
                source_md_path="reports/report.md",
                metadata_json=json.dumps({"demo": True, "showcase": True}, ensure_ascii=False),
                created_at=now,
                updated_at=now,
            )
            db.add(report)

            session_id = self._seed_conversation(db, project_id, now)
            self._seed_timeline_records(db, project_id, session_id, now)
            self._seed_memory(db, project_id, session_id, workspace_path, now)
            self._write_workspace_state(workspace_path, project_id, files, artifacts)
            db.commit()
            return {"project_id": project_id, "session_id": session_id}
        finally:
            db.close()

    def _ensure_existing_demo_ready(self, db, project: Project) -> str | None:
        project_id = project.id
        workspace_path = resolve_project_path(project.workspace_path)
        manifest_path = workspace_path / ".analysis" / "project_manifest.json"
        workspace_missing = not manifest_path.exists()
        if workspace_missing:
            workspace_path = self.workspace_manager.create_workspace(project_id).resolve()
            project.workspace_path = str(workspace_path)

        now = datetime.now().isoformat()
        files = self._ensure_demo_files(db, project, workspace_path, now)
        artifacts = db.query(Artifact).filter(Artifact.project_id == project_id).all()
        registered_paths = {artifact.path for artifact in artifacts}
        expected_dashboard_paths = {
            f"artifacts/charts/dashboard/{chart_id}.png"
            for chart_id in DEFAULT_DASHBOARD_CHART_IDS
        }
        artifact_missing = (
            any(not (workspace_path / artifact.path).exists() for artifact in artifacts)
            or not expected_dashboard_paths.issubset(registered_paths)
        )
        if workspace_missing or not artifacts or artifact_missing:
            db.query(Artifact).filter(Artifact.project_id == project_id).delete()
            artifacts = self._create_artifacts(db, project_id, workspace_path, now)
        if not db.query(Report).filter(Report.project_id == project_id).first():
            db.add(Report(
                id=f"rep_{uuid.uuid4().hex[:12]}",
                project_id=project_id,
                status="ready",
                title="Keemart Demo Report",
                source_md_path="reports/report.md",
                metadata_json=json.dumps({"demo": True, "showcase": True}, ensure_ascii=False),
                created_at=now,
                updated_at=now,
            ))

        session = (
            db.query(AnalysisSession)
            .filter(AnalysisSession.project_id == project_id, AnalysisSession.id == DEMO_SESSION_ID)
            .first()
            or db.query(AnalysisSession).filter(AnalysisSession.project_id == project_id).first()
        )
        session_id = session.id if session else self._seed_conversation(db, project_id, now)

        project.status = "report_ready"
        project.current_stage = "report_ready"
        project.updated_at = now
        self._write_workspace_state(workspace_path, project_id, files, artifacts)
        return session_id

    def _ensure_demo_files(self, db, project: Project, workspace_path: Path, now: str) -> list[ProjectFile]:
        mappings = [
            ("data/raw/order_info.csv", "order_info"),
            ("data/raw/exposure_info.csv", "exposure_info"),
            ("data/raw/activity_timeline.csv", "activity_timeline"),
            ("data/processed/category_date_panel.csv", "category_day_panel"),
        ]
        records: list[ProjectFile] = []
        for rel_path, role in mappings:
            source = FIXTURES_ROOT / rel_path
            target = workspace_path / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            record = (
                db.query(ProjectFile)
                .filter(ProjectFile.project_id == project.id, ProjectFile.role == role)
                .first()
            )
            if not record:
                record = ProjectFile(
                    id=f"file_{uuid.uuid4().hex[:12]}",
                    project_id=project.id,
                    role=role,
                    original_name=source.name,
                    current_path=rel_path,
                    created_at=now,
                )
                db.add(record)
            record.original_name = source.name
            record.current_path = rel_path
            record.size_bytes = target.stat().st_size
            record.checksum = compute_file_checksum(target)
            record.status = "validated" if role != "category_day_panel" else "generated"
            record.updated_at = now
            records.append(record)

        technical = workspace_path / "reports" / "technical_analysis_report.md"
        technical.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FIXTURES_ROOT / "reports" / "technical_analysis_report.md", technical)
        (workspace_path / "reports" / "report.md").write_text(_demo_report(project.id), encoding="utf-8")
        return records

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

        technical = workspace_path / "reports" / "technical_analysis_report.md"
        technical.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FIXTURES_ROOT / "reports" / "technical_analysis_report.md", technical)
        (workspace_path / "reports" / "report.md").write_text(_demo_report(project.id), encoding="utf-8")
        return records

    def _create_artifacts(self, db, project_id: str, workspace_path: Path, now: str) -> list[Artifact]:
        artifacts = []
        copied_specs = [
            (
                "artifacts/tables/category_action_recommendations.csv",
                "artifacts/tables/category_action_recommendations.csv",
                "table",
                "Category action recommendations",
                "text/csv",
            ),
            ("artifacts/charts/time_trends.png", "artifacts/charts/time_trends.png", "chart", "Demo time trends", "image/png"),
        ]
        for source_rel, target_rel, artifact_type, title, mime_type in copied_specs:
            source = FIXTURES_ROOT / source_rel
            target = workspace_path / target_rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            artifacts.append(self._add_artifact(db, project_id, artifact_type, title, target_rel, mime_type, target, now))

        generated_specs = [
            ("data/processed/category_day_panel.json", "panel_data", "category_day_panel.json", "application/json", _demo_panel_rows()),
            ("artifacts/charts/gmv_trend.json", "chart", "gmv_trend.json", "application/json", _demo_gmv_trend()),
            ("artifacts/charts/localgap.json", "chart", "localgap.json", "application/json", _demo_localgap_chart()),
            (".analysis/diagnostics_result.json", "diagnostics_result", "diagnostics_result.json", "application/json", _demo_diagnostics()),
            (".analysis/localgap_result.json", "localgap_result", "localgap_result.json", "application/json", _demo_localgap()),
            (".analysis/psm_did_result.json", "psm_did_result", "psm_did_result.json", "application/json", _demo_psm_did()),
        ]
        for target_rel, artifact_type, title, mime_type, data in generated_specs:
            target = workspace_path / target_rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            artifacts.append(self._add_artifact(db, project_id, artifact_type, title, target_rel, mime_type, target, now))

        for chart_id in DEFAULT_DASHBOARD_CHART_IDS:
            target = render_dashboard_chart(workspace_path, chart_id)
            target_rel = target.relative_to(workspace_path).as_posix()
            artifacts.append(self._add_artifact(db, project_id, "dashboard_chart", f"{chart_id}.png", target_rel, "image/png", target, now))

        report_target = workspace_path / "reports" / "report.md"
        artifacts.append(self._add_artifact(db, project_id, "report", "report.md", "reports/report.md", "text/markdown", report_target, now))
        return artifacts

    @staticmethod
    def _add_artifact(db, project_id: str, artifact_type: str, title: str, rel_path: str, mime_type: str, full_path: Path, now: str) -> Artifact:
        artifact = Artifact(
            id=f"art_{uuid.uuid4().hex[:12]}",
            project_id=project_id,
            type=artifact_type,
            title=title,
            path=rel_path,
            mime_type=mime_type,
            metadata_json=json.dumps({"demo": True, "showcase": True}, ensure_ascii=False),
            checksum=compute_file_checksum(full_path),
            created_at=now,
        )
        db.add(artifact)
        return artifact

    def _seed_conversation(self, db, project_id: str, now: str) -> str:
        session = AnalysisSession(
            id=DEMO_SESSION_ID,
            project_id=project_id,
            runtime_provider="demo",
            external_session_id=None,
            status="active",
            created_at=now,
            updated_at=now,
        )
        db.add(session)

        turns = [
            (
                "demo_full_turn_data_ready",
                "这个演示项目现在数据、报告和看板都准备好了吗？",
                "已经准备好。这个全流程 Demo 已加载订单、曝光、活动时间线三张表，并预置了 Pipeline 运行记录、Dashboard 产物、报告和 Memory 候选，适合直接演示。",
                [],
            ),
            (
                "demo_full_turn_increment",
                "请演示一次完整促销分析：审批、跑 pipeline、看结果、沉淀记忆。",
                "演示结论：活动期 GMV 和购买 UV 抬升明显，但增量主要来自 Drinks 曝光放大和发薪日前置；Baby 更适合控折扣保利润，Rice/Oil 适合围绕发薪日提前预热。报告、图表、Timeline 和 Memory Review 都已准备好。",
                [
                    {"type": "tool_call_started", "tool": "business_analysis", "action": "analysis.run_full_pipeline", "payload": {}},
                    {"type": "approval_requested", "approval_id": "demo_approval_full_pipeline", "action": "analysis.run_full_pipeline", "reason": "完整 pipeline 会写入分析产物和报告，需要 UI 审批。", "risk_level": "high", "payload": {}},
                    {"type": "job_started", "job_id": "demo_job_full_pipeline", "action": "analysis.run_full_pipeline", "message": "Starting approved analysis pipeline."},
                    {"type": "job_progress", "job_id": "demo_job_full_pipeline", "progress": 0.25, "message": "Panel and diagnostics completed."},
                    {"type": "job_progress", "job_id": "demo_job_full_pipeline", "progress": 0.65, "message": "PSM-DID and LocalGap completed."},
                    {"type": "artifact_created", "artifact_id": "demo_report", "name": "Keemart Demo Report", "path": "reports/report.md"},
                    {"type": "job_finished", "job_id": "demo_job_full_pipeline", "ok": True, "message": "Pipeline completed."},
                    {"type": "tool_call_finished", "tool": "business_analysis", "action": "analysis.run_full_pipeline", "ok": True, "summary": "完整 pipeline、图表、报告和记忆候选已生成。"},
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

    def _seed_timeline_records(self, db, project_id: str, session_id: str, now: str) -> None:
        job = Job(
            id="demo_job_full_pipeline",
            project_id=project_id,
            session_id=session_id,
            turn_id="demo_full_turn_increment",
            action="analysis.run_full_pipeline",
            status="succeeded",
            progress=1,
            input_json=json.dumps({"demo": True}, ensure_ascii=False),
            output_json=json.dumps({"steps": ["data.validate", "panel.build_category_day", "analysis.run_diagnostics", "analysis.run_localgap", "report.generate"]}, ensure_ascii=False),
            started_at=now,
            finished_at=now,
            created_at=now,
        )
        db.add(job)

        approval = ApprovalRequest(
            id="demo_approval_full_pipeline",
            project_id=project_id,
            session_id=session_id,
            turn_id="demo_full_turn_increment",
            tool_call_id="demo_tool_full_pipeline",
            action="analysis.run_full_pipeline",
            reason="完整 pipeline 会写入图表、报告和记忆候选，演示中已审批。",
            risk_level="high",
            payload_json=json.dumps({}, ensure_ascii=False),
            status="approved",
            created_at=now,
            resolved_at=now,
            resolved_by="demo",
        )
        db.add(approval)

        for action, status, summary in [
            ("data.validate", "succeeded", "三张核心 CSV 校验通过。"),
            ("panel.build_category_day", "succeeded", "生成 category x day panel。"),
            ("analysis.run_diagnostics", "succeeded", "输出 GMV 趋势、活动期对比和品类集中度。"),
            ("analysis.run_psm_did", "succeeded", "完成方向性 DID 估计。"),
            ("analysis.run_localgap", "succeeded", "拆解曝光、折扣和发薪日贡献。"),
            ("report.generate", "succeeded", "生成 Markdown 分析报告。"),
        ]:
            db.add(ToolCall(
                id=f"demo_tool_{action.replace('.', '_')}",
                session_id=session_id,
                turn_id="demo_full_turn_increment",
                project_id=project_id,
                tool_name="business_analysis",
                action=action,
                payload_json=json.dumps({}, ensure_ascii=False),
                payload_hash=f"sha256:{uuid.uuid4().hex}",
                status=status,
                result_json=json.dumps({"ok": True, "summary": summary}, ensure_ascii=False),
                permission_level=3 if action in {"panel.build_category_day", "report.generate"} else 1,
                created_at=now,
                completed_at=now,
            ))

    def _seed_memory(self, db, project_id: str, session_id: str, workspace_path: Path, now: str) -> None:
        pending = "Drinks 增量主要由曝光放大驱动；下一轮活动建议提高活动坑位和站内推荐资源。"
        approved = "Keemart Demo 已确认：发薪日前置会放大 Rice/Oil 与 Drinks 类目的转化，应在活动前 1-2 天完成预热。"
        db.add(MemoryCandidate(
            id="demo_memory_pending_drinks",
            project_id=project_id,
            session_id=session_id,
            turn_id="demo_full_turn_increment",
            scope="project",
            content=pending,
            source_artifact_ids="demo_report",
            status="pending",
            created_at=now,
        ))
        db.add(MemoryCandidate(
            id="demo_memory_approved_payday",
            project_id=project_id,
            session_id=session_id,
            turn_id="demo_full_turn_increment",
            scope="project",
            content=approved,
            source_artifact_ids="demo_report",
            status="approved",
            created_at=now,
            resolved_at=now,
        ))
        memory_path = workspace_path / ".analysis" / "memory_candidates.md"
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        memory_path.write_text(
            "# 记忆库\n\n---\n"
            f"**时间**: {now}\n"
            "**范围**: project\n\n"
            f"{approved}\n",
            encoding="utf-8",
        )

    def _write_workspace_state(self, workspace_path: Path, project_id: str, files: list[ProjectFile], artifacts: list[Artifact]) -> None:
        latest_result = {
            "demo": True,
            "stage": "report_ready",
            "diagnostics": _demo_diagnostics(),
            "localgap": _demo_localgap(),
            "psm_did": _demo_psm_did(),
            "recommended_actions": [
                {"category": "drinks", "action": "scale_exposure", "reason": "曝光贡献最高，适合扩量。"},
                {"category": "baby", "action": "optimize_discount", "reason": "控制折扣深度，优先保利润。"},
                {"category": "rice_oil", "action": "payday_timing", "reason": "围绕发薪日前置触达。"},
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
            completed_tasks="data_ingest, schema_infer, panel_build, diagnostics, localgap, report_generate, memory_review",
            latest_artifact="reports/report.md; artifacts/charts/gmv_trend.json; artifacts/charts/localgap.json",
            conclusions="活动期 GMV 与购买 UV 抬升；Drinks 加码曝光，Baby 控折扣优化，Rice/Oil 发薪日前置。",
            pending_items="生产决策前需要完整利润口径和实验验证。",
            next_steps="演示 Agent、Timeline、Dashboard、Reports、Memory 全流程。",
        )


def _demo_diagnostics() -> dict:
    return {
        "summary": {"total_gmv": 1984.4, "total_days": 7, "total_categories": 4, "activity_days": 4},
        "category_concentration": [
            {"category": "drinks", "gmv": 639.7, "share": 32.24},
            {"category": "baby", "gmv": 630.3, "share": 31.76},
            {"category": "rice_oil", "gmv": 480.0, "share": 24.19},
            {"category": "beauty", "gmv": 234.4, "share": 11.81},
        ],
    }


def _demo_localgap() -> dict:
    return {
        "total_actual_gmv": 655.6,
        "total_baseline_gmv": 218.5,
        "total_local_gap": 437.1,
        "categories": [
            {"category": "drinks", "baseline_gmv": 120.5, "actual_gmv": 519.2, "local_gap": 398.7, "exposure_gap": 221.4, "discount_gap": 4.68, "payday_gap": 53.7},
            {"category": "beauty", "baseline_gmv": 98.0, "actual_gmv": 136.4, "local_gap": 38.4, "exposure_gap": 18.2, "discount_gap": 6.5, "payday_gap": 0},
        ],
    }


def _demo_psm_did() -> dict:
    return {
        "estimates": {"did_estimate": -111.49, "treated_pre_avg": 0, "treated_post_avg": 0, "control_pre_avg": 109.25, "control_post_avg": 220.74},
        "lift": {"treated_lift_pct": 0, "control_lift_pct": 102.05},
        "interpretation": "方向性结果提示自然周期和发薪日贡献需要单独拆分，不能把全部抬升归因给折扣。",
    }


def _demo_panel_rows() -> list[dict]:
    return [
        {"date": "2026-04-25", "category": "drinks", "gmv": 120.5, "exposure": 800, "discount_rate": 8.2, "is_activity": False},
        {"date": "2026-04-26", "category": "drinks", "gmv": 519.2, "exposure": 2400, "discount_rate": 9.1, "is_activity": True},
        {"date": "2026-04-25", "category": "baby", "gmv": 305.0, "exposure": 650, "discount_rate": 12.5, "is_activity": False},
        {"date": "2026-04-26", "category": "baby", "gmv": 325.3, "exposure": 720, "discount_rate": 10.8, "is_activity": True},
    ]


def _demo_gmv_trend() -> dict:
    return {
        "title": "GMV trend",
        "series": [
            {"date": "2026-04-24", "gmv": 260.4},
            {"date": "2026-04-25", "gmv": 438.8},
            {"date": "2026-04-26", "gmv": 655.6},
            {"date": "2026-04-27", "gmv": 629.6},
        ],
    }


def _demo_localgap_chart() -> dict:
    return {
        "title": "LocalGap decomposition",
        "series": [
            {"category": "drinks", "exposure_gap": 221.4, "discount_gap": 4.68, "payday_gap": 53.7},
            {"category": "beauty", "exposure_gap": 18.2, "discount_gap": 6.5, "payday_gap": 0},
        ],
    }


def _demo_report(project_id: str) -> str:
    return f"""# Keemart 促销增长全流程演示报告

**项目ID**: {project_id}

## 一页结论

- 活动期 GMV 与购买 UV 抬升明显，但不能直接把全部增量归因给折扣。
- Drinks 的增量主要来自曝光放大，适合扩大活动资源位。
- Baby 类目折扣贡献有限，建议控制折扣深度，优先保证利润。
- Rice/Oil 对发薪日前置更敏感，适合提前 1-2 天预热。

## 已完成链路

1. Data Intake: 三张 CSV 已加载并校验。
2. Panel Build: 已生成 category x day panel。
3. Diagnostics: 已输出趋势、集中度、活动期对比。
4. Causal Direction: 已完成方向性 PSM-DID。
5. LocalGap: 已拆分曝光、折扣、发薪日贡献。
6. Reports & Memory: 报告和记忆候选已生成。

## 演示提示

请依次打开 Agent、Timeline、Dashboard、Reports、Memory 页面，可以看到完整闭环。
"""
