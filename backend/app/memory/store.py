import json
from pathlib import Path
from datetime import datetime
from typing import Optional


class MemoryStore:
    """
    项目级记忆存储

    记忆存储在 workspace/.analysis/memory_candidates.md
    不直接写入 ~/.claude（用户级记忆由前端处理）
    """

    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.memory_file = self.workspace_path / ".analysis" / "memory_candidates.md"

    def write_memory(self, content: str, scope: str = "project") -> bool:
        """
        将已审批的记忆写入 memory_candidates.md
        """
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

        entry = f"\n---\n"
        entry += f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        entry += f"**范围**: {scope}\n"
        entry += f"\n{content}\n"

        if self.memory_file.exists():
            existing = self.memory_file.read_text(encoding="utf-8")
            self.memory_file.write_text(existing + entry, encoding="utf-8")
        else:
            self.memory_file.write_text("# 记忆库\n" + entry, encoding="utf-8")

        return True

    def read_memory(self, scope: Optional[str] = None) -> str:
        """读取记忆内容"""
        if not self.memory_file.exists():
            return ""

        content = self.memory_file.read_text(encoding="utf-8")
        if scope is None:
            return content

        lines = content.split("\n")
        result_lines = []
        include_entry = False

        for line in lines:
            if line.startswith("**范围**:"):
                entry_scope = line.split(":", 1)[1].strip()
                include_entry = entry_scope == scope
            if include_entry or scope is None:
                result_lines.append(line)

        return "\n".join(result_lines)

    def list_memory_entries(self) -> list[dict]:
        """列出所有记忆条目"""
        if not self.memory_file.exists():
            return []

        content = self.memory_file.read_text(encoding="utf-8")
        entries = []
        current_entry = {}

        for line in content.split("\n"):
            if line.startswith("---"):
                if current_entry:
                    entries.append(current_entry)
                    current_entry = {}
            elif line.startswith("**时间**:"):
                current_entry["time"] = line.split(":", 1)[1].strip()
            elif line.startswith("**范围**:"):
                current_entry["scope"] = line.split(":", 1)[1].strip()

        if current_entry:
            entries.append(current_entry)

        return entries
