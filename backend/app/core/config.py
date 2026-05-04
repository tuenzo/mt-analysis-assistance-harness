from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# 加载 .env 文件（从项目根目录）
load_dotenv(Path(__file__).parent.parent.parent / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", env_file_encoding="utf-8")

    workspace_root: Path = Path("./workspaces")
    workspace_version: int = 1
    agent_runtime_provider: str = "mock"
    agent_permission_mode: str = "dontAsk"
    agent_enable_user_settings: bool = True
    agent_allow_builtin_read_tools: bool = False
    # 第三方 API 配置
    anthropic_api_key: str = ""
    anthropic_api_base_url: str = ""
    anthropic_api_model: str = "claude-opus-4-5-20250501"


settings = Settings()


def get_agent_runtime_config() -> dict:
    return {
        "provider": settings.agent_runtime_provider,
        "permission_mode": settings.agent_permission_mode,
        "enable_user_setting_sources": settings.agent_enable_user_settings,
        "allow_builtin_read_tools": settings.agent_allow_builtin_read_tools,
        "workspace_root": str(settings.workspace_root),
    }
