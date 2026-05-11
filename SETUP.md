# Local Setup

This repository includes a cross-platform setup program for local Windows and macOS deployment.

## First Run

Windows PowerShell:

```powershell
.\setup.ps1
```

macOS:

```bash
bash setup.sh
```

The default flow runs:

1. `configure` - create or update `.env`
2. `install` - create `backend/.venv`, install Python packages, and install frontend packages
3. `start` - start FastAPI and Next.js

The setup program prompts for:

- model provider: `longcat`, `anthropic`, `custom`, or `mock`
- model name
- API key
- API base URL when needed
- agent runtime provider: `claude_agent_sdk` or `mock`
- permission mode: `dontAsk` or `manual`

Secrets are written only to `.env`, which is git-ignored.

## Edit Model Settings Later

Run configuration mode any time:

```powershell
.\setup.ps1 configure
```

```bash
bash setup.sh configure
```

Existing non-secret values are shown as defaults. Leaving the API key blank keeps the existing key.

## Start and Stop Services

Start services from the current `.env`:

```powershell
.\setup.ps1 start
```

```bash
bash setup.sh start
```

Stop setup-managed services:

```powershell
.\setup.ps1 stop
```

```bash
bash setup.sh stop
```

Check service status:

```powershell
.\setup.ps1 status
```

```bash
bash setup.sh status
```

Setup writes runtime metadata and logs under `.codex-run/setup/`.

## Useful Options

Run without prompts:

```bash
bash setup.sh run-all --non-interactive --yes --provider mock
```

Use a custom provider:

```bash
bash setup.sh configure --provider custom --api-base-url https://example.com/anthropic
```

Use different ports:

```bash
bash setup.sh start --backend-port 18082 --frontend-port 3011
```

Skip dependency install during first run:

```bash
bash setup.sh run-all --skip-install
```

## Requirements

- Python 3.10+
- Node.js with npm
- Network access for dependency installation
