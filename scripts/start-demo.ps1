param(
  [int]$BackendPort = 18081,
  [int]$FrontendPort = 3010,
  [switch]$ResetDemo,
  [string]$AgentRuntimeProvider = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackendRoot = Join-Path $RepoRoot "backend"
$FrontendRoot = Join-Path $RepoRoot "frontend"
$RunRoot = Join-Path $BackendRoot ".codex-run"
$WorkspaceRoot = Join-Path $BackendRoot "workspaces"
$DatabasePath = Join-Path $RunRoot "demo-review-$BackendPort.db"

New-Item -ItemType Directory -Force -Path $RunRoot | Out-Null
New-Item -ItemType Directory -Force -Path $WorkspaceRoot | Out-Null

$PythonExe = Join-Path $BackendRoot ".venv\Scripts\python.exe"
if (!(Test-Path $PythonExe)) {
  $PythonExe = "python"
}

$BackendEnv = @"
`$env:APP_DATABASE_URL='sqlite:///$($DatabasePath.Replace('\', '/'))';
`$env:APP_WORKSPACE_ROOT='$WorkspaceRoot';
`$env:APP_DEMO_MODE='true';
`$env:APP_DEMO_PROJECT_ID='proj_demo_review';
`$env:APP_DEMO_RESET_ON_START='$($ResetDemo.IsPresent.ToString().ToLowerInvariant())';
`$env:APP_AGENT_PERMISSION_MODE='dontAsk';
"@

if ($AgentRuntimeProvider.Trim()) {
  $BackendEnv += "`$env:APP_AGENT_RUNTIME_PROVIDER='$AgentRuntimeProvider';"
}

$BackendCommand = "$BackendEnv cd '$BackendRoot'; & '$PythonExe' -m uvicorn app.main:app --host 127.0.0.1 --port $BackendPort"
$FrontendCommand = "`$env:NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:$BackendPort'; cd '$FrontendRoot'; npm run dev -- -H 127.0.0.1 -p $FrontendPort"

Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoExit", "-Command", $BackendCommand
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoExit", "-Command", $FrontendCommand

Write-Host "Demo backend:  http://127.0.0.1:$BackendPort"
Write-Host "Demo frontend: http://127.0.0.1:$FrontendPort/projects/proj_demo_review/dashboard"
