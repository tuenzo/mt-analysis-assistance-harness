## Why

当前配置硬编码在代码中或依赖环境变量，不方便管理。用户需要一个 `.env` 文件来集中管理敏感配置，并且该文件应该被 `.gitignore` 忽略以确保安全。

## What Changes

- **新增** `.env.example` — 模板文件，包含所有可配置项的示例
- **新增** `.gitignore` — 忽略 `.env`、数据库文件、日志等敏感文件
- **修改** `config.py` — 添加 `python-dotenv` 支持，从 `.env` 加载配置
- **移除** 硬编码的配置默认值，改用环境变量或 `.env` 文件

## Capabilities

### New Capabilities
- `env-file-configuration`: 通过 `.env` 文件管理敏感配置

### Modified Capabilities
- 无

## Impact

- **新建**: `.env.example`
- **新建**: `.gitignore`
- **修改**: `backend/app/core/config.py` — 加载 `.env` 文件
