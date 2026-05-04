## Overview

通过 `python-dotenv` 库加载 `.env` 文件中的环境变量，实现配置的集中管理和安全存储。

## 实现方案

### 1. 安装 python-dotenv

```
pip install python-dotenv
```

### 2. .env.example 模板

```env
# API 配置
ANTHROPIC_API_KEY=your_api_key_here
ANTHROPIC_API_BASE_URL=https://api.example.com/v1

# Agent Runtime
APP_AGENT_RUNTIME_PROVIDER=mock
APP_AGENT_PERMISSION_MODE=dontAsk
```

### 3. .gitignore

```
# 环境配置
.env
.env.local
.env.*.local

# 数据库
*.db
*.db-journal

# 日志
logs/
*.log

# Python
__pycache__/
*.py[cod]
*.pyc

# IDE
.vscode/
.idea/
*.swp
*.swo

# 工作区
workspaces/
```

### 4. config.py 修改

```python
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(Path(__file__).parent.parent.parent / ".env")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", env_file_encoding="utf-8")

    workspace_root: Path = Path("./workspaces")
    workspace_version: int = 1
    agent_runtime_provider: str = "mock"
    agent_permission_mode: str = "dontAsk"
    agent_enable_user_settings: bool = True
    agent_allow_builtin_read_tools: bool = False
    anthropic_api_key: str = ""
    anthropic_api_base_url: str = ""
```

## 配置优先级

1. 环境变量（最高优先级）
2. `.env` 文件
3. 代码默认值（最低优先级）
