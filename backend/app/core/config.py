from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_")

    workspace_root: Path = Path("./workspaces")
    workspace_version: int = 1
    agent_runtime_provider: str = "mock"
    agent_permission_mode: str = "dontAsk"
    agent_enable_user_settings: bool = True
    agent_allow_builtin_read_tools: bool = False


settings = Settings()


def get_agent_runtime_config() -> dict:
    return {
        "provider": settings.agent_runtime_provider,
        "permission_mode": settings.agent_permission_mode,
        "enable_user_setting_sources": settings.agent_enable_user_settings,
        "allow_builtin_read_tools": settings.agent_allow_builtin_read_tools,
        "workspace_root": str(settings.workspace_root),
    }
