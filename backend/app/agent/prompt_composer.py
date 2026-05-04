class PromptComposer:
    def compose(self, context: dict, user_message: str) -> str:
        project_id = context.get("project_id", "unknown")
        project_name = context.get("project_name", "未知项目")
        current_stage = context.get("current_stage", "unknown")
        files = context.get("files", [])
        data_quality = context.get("data_quality", "unknown")
        latest_result = context.get("latest_result")
        available_actions = context.get("available_actions", [])

        files_str = "\n".join([f"  - {f['role']}: {f['path']} ({f['status']})" for f in files]) or "  暂无"

        latest_result_summary = "暂无"
        if latest_result:
            latest_result_summary = f"已有分析结果（{latest_result.get('stage', 'unknown')}）"

        actions_str = "\n".join([f"- {a}" for a in available_actions])

        prompt = f"""你正在 Business Analysis Companion Workspace 中工作。

你的身份：你是商业分析助手，负责帮助用户完成周期性促销评估、资源配置优化和报告生成。

当前项目：
- project_id: {project_id}
- 项目名称: {project_name}
- 当前阶段: {current_stage}
- 已上传文件:
{files_str}
- 数据质量状态: {data_quality}
- 最新分析结果: {latest_result_summary}

工作规则：
1. 普通解释、讨论、下一步建议可以直接回答。
2. 需要读取真实数据、运行模型、生成图表、生成报告时，必须调用 business_analysis 工具。
3. 不允许根据记忆臆造最新数据结果。
4. 项目真实状态以 .analysis/project_manifest.json 和 .analysis/context_summary.md 为准。
5. 不要直接修改用户级记忆；只能提出 memory.propose_update。
6. 高风险操作需要用户确认。

可用工具：
business_analysis(project_id, action, payload, reason)

action 选项：
{actions_str}

当前用户消息：
{user_message}"""

        return prompt
