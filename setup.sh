#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_SCRIPT="$REPO_ROOT/scripts/local_setup.py"

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$SETUP_SCRIPT" "$@"
fi

if command -v python >/dev/null 2>&1; then
  exec python "$SETUP_SCRIPT" "$@"
fi

echo "Python was not found. Install Python 3.10+ and rerun setup." >&2
exit 1
