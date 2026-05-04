from pathlib import Path
from typing import Optional


CONTEXT_SUMMARY_TEMPLATE = """# 项目: {project_name}

## 当前阶段: {current_stage}

## 数据文件状态
{file_status}

## 字段映射状态
{schema_status}

## 已完成任务
{completed_tasks}

## 最新 artifact
{latest_artifact}

## 核心结论
{conclusions}

## 待确认事项
{pending_items}

## 下一步建议
{next_steps}
"""


class ContextSummaryWriter:
    DEFAULT_CONTENT = """# 项目: 新项目

## 当前阶段: created

## 数据文件状态
暂无文件

## 字段映射状态
未开始

## 已完成任务
无

## 最新 artifact
无

## 核心结论
无

## 待确认事项
无

## 下一步建议
上传 order_info.csv、exposure_info.csv、activity_timeline.csv
"""

    def __init__(self, workspace_path: Path):
        self.workspace_path = Path(workspace_path)
        self.file_path = workspace_path / ".analysis" / "context_summary.md"

    def init_default(self, project_name: str) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        content = self.DEFAULT_CONTENT.replace("新项目", project_name)
        self.file_path.write_text(content, encoding="utf-8")

    def write(self, project_name: str, current_stage: str, file_status: str = "暂无文件",
              schema_status: str = "未开始", completed_tasks: str = "无",
              latest_artifact: str = "无", conclusions: str = "无",
              pending_items: str = "无", next_steps: str = "上传数据文件") -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        content = CONTEXT_SUMMARY_TEMPLATE.format(
            project_name=project_name,
            current_stage=current_stage,
            file_status=file_status,
            schema_status=schema_status,
            completed_tasks=completed_tasks,
            latest_artifact=latest_artifact,
            conclusions=conclusions,
            pending_items=pending_items,
            next_steps=next_steps
        )
        self.file_path.write_text(content, encoding="utf-8")

    @staticmethod
    def read(workspace_path: Path) -> str:
        path = Path(workspace_path) / ".analysis" / "context_summary.md"
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")
