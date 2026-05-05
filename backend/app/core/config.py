import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env from the backend directory.
load_dotenv(Path(__file__).parent.parent.parent / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", env_file_encoding="utf-8")

    workspace_root: Path = Path("./workspaces")
    workspace_version: int = 1
    agent_runtime_provider: str = "mock"
    agent_permission_mode: str = "dontAsk"
    agent_enable_user_settings: bool = True
    agent_allow_builtin_read_tools: bool = False
    test_mode: bool = False
    demo_mode: bool = False
    demo_project_id: str = "proj_demo_keemart_promo"
    demo_reset_on_start: bool = True
    # Third-party model/API configuration.
    anthropic_api_key: str = ""
    anthropic_api_base_url: str = ""
    anthropic_api_model: str = "claude-opus-4-5-20250501"


settings = Settings()


def is_test_mode() -> bool:
    value = os.getenv("APP_TEST_MODE")
    if value is None:
        return settings.test_mode
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def is_demo_mode() -> bool:
    return _env_bool("APP_DEMO_MODE", settings.demo_mode)


def demo_reset_on_start() -> bool:
    return _env_bool("APP_DEMO_RESET_ON_START", settings.demo_reset_on_start)


def get_demo_project_id() -> str:
    return os.getenv("APP_DEMO_PROJECT_ID", settings.demo_project_id)


def get_agent_runtime_config() -> dict:
    return {
        "provider": settings.agent_runtime_provider,
        "permission_mode": settings.agent_permission_mode,
        "enable_user_setting_sources": settings.agent_enable_user_settings,
        "allow_builtin_read_tools": settings.agent_allow_builtin_read_tools,
        "workspace_root": str(settings.workspace_root),
    }
