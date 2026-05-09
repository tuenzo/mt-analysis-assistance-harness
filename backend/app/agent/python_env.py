from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PythonEnvironment:
    venv_path: Path | None
    python_executable: Path | None
    scripts_path: Path | None
    source: str

    @property
    def available(self) -> bool:
        return bool(self.venv_path and self.python_executable and self.python_executable.exists())

    def as_dict(self) -> dict[str, str | bool]:
        return {
            "available": self.available,
            "venv_path": str(self.venv_path) if self.venv_path else "",
            "python_executable": str(self.python_executable) if self.python_executable else "",
            "scripts_path": str(self.scripts_path) if self.scripts_path else "",
            "source": self.source,
        }


def discover_python_environment(workspace_path: str | Path | None = None) -> PythonEnvironment:
    """Find the Python environment the agent runtime should inherit."""

    candidates = _candidate_venv_paths(Path(workspace_path).resolve() if workspace_path else None)
    for source, path in candidates:
        env = _environment_from_path(path, source)
        if env.available:
            return env
    return PythonEnvironment(venv_path=None, python_executable=None, scripts_path=None, source="unavailable")


def apply_python_environment(env: dict[str, str], workspace_path: str | Path | None = None) -> dict[str, str]:
    """Return an env dict with the discovered venv activated for child runtimes."""

    python_env = discover_python_environment(workspace_path)
    if not python_env.available:
        return env

    updated = dict(env)
    updated["VIRTUAL_ENV"] = str(python_env.venv_path)
    updated["PYTHONUTF8"] = "1"
    updated["PYTHONIOENCODING"] = "utf-8"
    current_path = updated.get("PATH") or os.environ.get("PATH", "")
    scripts_path = str(python_env.scripts_path)
    path_parts = [part for part in current_path.split(os.pathsep) if part]
    if scripts_path not in path_parts:
        updated["PATH"] = os.pathsep.join([scripts_path, *path_parts])
    return updated


def _candidate_venv_paths(workspace_path: Path | None) -> list[tuple[str, Path]]:
    repo_root = Path(__file__).resolve().parents[3]
    candidates: list[tuple[str, Path]] = []

    env_virtual_env = os.environ.get("VIRTUAL_ENV")
    if env_virtual_env:
        candidates.append(("env:VIRTUAL_ENV", Path(env_virtual_env)))

    if workspace_path:
        candidates.extend(
            [
                ("workspace:.venv", workspace_path / ".venv"),
                ("workspace:venv", workspace_path / "venv"),
            ]
        )

    candidates.extend(
        [
            ("backend:.venv", repo_root / "backend" / ".venv"),
            ("repo:.venv", repo_root / ".venv"),
        ]
    )
    return candidates


def _environment_from_path(path: Path, source: str) -> PythonEnvironment:
    scripts_path = path / ("Scripts" if os.name == "nt" else "bin")
    python_name = "python.exe" if os.name == "nt" else "python"
    python_executable = scripts_path / python_name
    return PythonEnvironment(
        venv_path=path if path.exists() else None,
        python_executable=python_executable if python_executable.exists() else None,
        scripts_path=scripts_path if scripts_path.exists() else None,
        source=source,
    )
