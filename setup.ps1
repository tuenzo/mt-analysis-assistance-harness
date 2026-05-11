param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$SetupArgs
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SetupScript = Join-Path $RepoRoot "scripts\local_setup.py"

$Python = Get-Command python -ErrorAction SilentlyContinue
if ($Python) {
  & $Python.Source $SetupScript @SetupArgs
  exit $LASTEXITCODE
}

$PyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($PyLauncher) {
  & $PyLauncher.Source -3 $SetupScript @SetupArgs
  exit $LASTEXITCODE
}

Write-Error "Python was not found. Install Python 3.10+ and rerun setup."
exit 1
