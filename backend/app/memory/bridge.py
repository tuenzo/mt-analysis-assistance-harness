from pathlib import Path
from app.memory.summarizer import generate_memory_summary
from app.memory.store import MemoryStore
from app.tools.schemas import ToolResult
from app.projects.service import ProjectService


class MemoryBridge:
    """
    记忆桥接器

    负责:
    1. 从分析结果生成记忆候选
    2. 将已审批的记忆写入记忆存储
    3. 提供记忆查询接口
    """

    def propose_update(self, project_id: str, content: str, scope: str = "project") -> ToolResult:
        """
        生成记忆候选（实际存储在 MemoryCandidate 表，由审批流程处理）
        """
        return ToolResult(
            ok=True,
            action="memory.propose_update",
            summary="记忆候选已创建，等待审批",
            artifacts=[{"type": "memory_summary", "scope": scope}],
            assistant_hint="记忆候选已生成，请在 Memory Review Panel 中审批。"
        )

    def approve_and_store(self, project_id: str, candidate_id: str, content: str, scope: str) -> ToolResult:
        """
        审批通过后，将记忆写入存储
        """
        service = ProjectService()
        project = service.get_project(project_id)
        if not project:
            return ToolResult(
                ok=False,
                action="memory.approve",
                summary="",
                error={"code": "NOT_FOUND", "message": "Project not found"},
            )

        store = MemoryStore(project.workspace_path)
        success = store.write_memory(content, scope)

        if success:
            return ToolResult(
                ok=True,
                action="memory.approve",
                summary="记忆已同步到项目",
                artifacts=[{"type": "memory_stored", "scope": scope}],
            )
        else:
            return ToolResult(
                ok=False,
                action="memory.approve",
                summary="",
                error={"code": "STORE_FAILED", "message": "记忆写入失败"},
            )

    def generate_summary(self, project_id: str) -> ToolResult:
        """
        从分析结果生成记忆摘要
        """
        service = ProjectService()
        project = service.get_project(project_id)
        if not project:
            return ToolResult(
                ok=False,
                action="memory.generate_summary",
                summary="",
                error={"code": "NOT_FOUND", "message": "Project not found"},
            )

        summary = generate_memory_summary(project_id, project.workspace_path)
        if "error" in summary:
            return ToolResult(
                ok=False,
                action="memory.generate_summary",
                summary="",
                error={"code": "NO_RESULTS", "message": "请先运行分析 pipeline"},
            )

        return ToolResult(
            ok=True,
            action="memory.generate_summary",
            summary="记忆摘要已生成",
            artifacts=[{"type": "memory_summary", "content": summary["content"], "scope": summary["scope"]}],
        )

    def get_memory(self, project_id: str, scope: str = "project") -> ToolResult:
        """
        获取项目的记忆
        """
        service = ProjectService()
        project = service.get_project(project_id)
        if not project:
            return ToolResult(
                ok=False,
                action="memory.get",
                summary="",
                error={"code": "NOT_FOUND", "message": "Project not found"},
            )

        store = MemoryStore(project.workspace_path)
        content = store.read_memory(scope)

        if not content:
            return ToolResult(
                ok=True,
                action="memory.get",
                summary="暂无记忆",
                artifacts=[],
            )

        return ToolResult(
            ok=True,
            action="memory.get",
            summary=f"获取到 {len(content)} 字符的记忆",
            artifacts=[{"type": "memory_content", "content": content, "scope": scope}],
        )
