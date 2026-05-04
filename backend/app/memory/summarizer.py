import json
from pathlib import Path
from datetime import datetime


def generate_memory_summary(project_id: str, workspace_path: str) -> dict:
    """
    从分析结果生成记忆摘要
    """
    workspace_path = Path(workspace_path)
    analysis_dir = workspace_path / ".analysis"

    latest_result_path = analysis_dir / "latest_result.json"
    if not latest_result_path.exists():
        return {"error": "no_results"}

    results = json.loads(latest_result_path.read_text(encoding="utf-8"))

    diagnostics = results.get("diagnostics", {})
    localgap = results.get("localgap", {})

    summary_parts = []

    summary_parts.append(f"## 项目 {project_id} 记忆摘要\n")
    summary_parts.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    if diagnostics:
        summary_parts.append("### 数据概况\n")
        s = diagnostics.get("summary", {})
        summary_parts.append(f"- 总 GMV: {s.get('total_gmv', 'N/A')}")
        summary_parts.append(f"- 品类数: {s.get('total_categories', 'N/A')}")
        summary_parts.append(f"- 分析天数: {s.get('total_days', 'N/A')}")
        summary_parts.append("")

    if localgap:
        summary_parts.append("### 增量贡献\n")
        for cat in localgap.get("categories", [])[:3]:
            summary_parts.append(f"- {cat.get('category')}: gap={cat.get('local_gap')}")
        summary_parts.append("")

    return {
        "content": "\n".join(summary_parts),
        "scope": "project",
        "project_id": project_id,
    }
