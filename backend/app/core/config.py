from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    workspace_root: Path = Path("./workspaces")
    workspace_version: int = 1

    class Config:
        env_prefix = "APP_"


settings = Settings()
