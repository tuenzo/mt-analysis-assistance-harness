from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_")

    workspace_root: Path = Path("./workspaces")
    workspace_version: int = 1


settings = Settings()
