#!/usr/bin/env python3
"""Cross-platform local setup for the business analysis harness."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.error import URLError
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
FRONTEND_ROOT = REPO_ROOT / "frontend"
ENV_PATH = REPO_ROOT / ".env"
RUN_DIR = REPO_ROOT / ".codex-run" / "setup"
STATE_PATH = RUN_DIR / "services.json"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_BACKEND_PORT = 18081
DEFAULT_FRONTEND_PORT = 3010
DEFAULT_WORKSPACE_ROOT = "./workspaces"

MANAGED_KEYS = [
    "APP_MODEL_PROVIDER",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_API_BASE_URL",
    "ANTHROPIC_API_MODEL",
    "APP_AGENT_RUNTIME_PROVIDER",
    "APP_AGENT_PERMISSION_MODE",
    "APP_WORKSPACE_ROOT",
    "APP_TEST_MODE",
    "APP_DEMO_MODE",
    "NEXT_PUBLIC_API_BASE_URL",
]


@dataclass(frozen=True)
class ProviderPreset:
    key: str
    label: str
    runtime_provider: str
    model: str
    api_base_url: str
    requires_api_key: bool = True


PROVIDER_PRESETS: dict[str, ProviderPreset] = {
    "longcat": ProviderPreset(
        key="longcat",
        label="LongCat Anthropic-compatible API",
        runtime_provider="claude_agent_sdk",
        model="LongCat-Flash-Chat",
        api_base_url="https://api.longcat.chat/anthropic",
    ),
    "anthropic": ProviderPreset(
        key="anthropic",
        label="Anthropic official API",
        runtime_provider="claude_agent_sdk",
        model="claude-opus-4-5-20250501",
        api_base_url="",
    ),
    "custom": ProviderPreset(
        key="custom",
        label="Custom Anthropic-compatible API",
        runtime_provider="claude_agent_sdk",
        model="",
        api_base_url="",
    ),
    "mock": ProviderPreset(
        key="mock",
        label="Local mock runtime",
        runtime_provider="mock",
        model="mock",
        api_base_url="",
        requires_api_key=False,
    ),
}


@dataclass
class ModelConfig:
    provider: str
    api_key: str
    api_base_url: str
    model: str
    runtime_provider: str
    permission_mode: str
    workspace_root: str
    backend_port: int
    frontend_port: int
    host: str

    @property
    def api_base(self) -> str:
        return f"http://{self.host}:{self.backend_port}"

    def to_env_updates(self) -> dict[str, str]:
        return {
            "APP_MODEL_PROVIDER": self.provider,
            "ANTHROPIC_API_KEY": self.api_key,
            "ANTHROPIC_API_BASE_URL": self.api_base_url,
            "ANTHROPIC_API_MODEL": self.model,
            "APP_AGENT_RUNTIME_PROVIDER": self.runtime_provider,
            "APP_AGENT_PERMISSION_MODE": self.permission_mode,
            "APP_WORKSPACE_ROOT": self.workspace_root,
            "APP_TEST_MODE": "false",
            "APP_DEMO_MODE": "false",
            "NEXT_PUBLIC_API_BASE_URL": self.api_base,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def strip_inline_comment(value: str) -> str:
    quote: str | None = None
    for index, char in enumerate(value):
        if char in {"'", '"'}:
            if quote == char:
                quote = None
            elif quote is None:
                quote = char
        if char == "#" and quote is None:
            if index == 0 or value[index - 1].isspace():
                return value[:index].rstrip()
    return value.strip()


def parse_env_value(raw: str) -> str:
    value = strip_inline_comment(raw.strip())
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value


def read_dotenv(path: Path = ENV_PATH) -> tuple[list[str], dict[str, str]]:
    if not path.exists():
        return [], {}
    lines = path.read_text(encoding="utf-8").splitlines()
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if key:
            values[key] = parse_env_value(raw_value)
    return lines, values


def format_env_value(value: str) -> str:
    value = "" if value is None else str(value)
    if value == "":
        return ""
    needs_quotes = any(char.isspace() for char in value) or "#" in value
    if not needs_quotes:
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def line_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in line:
        return None
    key = line.split("=", 1)[0].strip()
    return key or None


def write_dotenv(
    path: Path,
    updates: dict[str, str],
    *,
    managed_keys: Iterable[str] = MANAGED_KEYS,
) -> None:
    lines, _ = read_dotenv(path)
    updated_lines: list[str] = []
    seen: set[str] = set()

    for line in lines:
        key = line_key(line)
        if key and key in updates:
            updated_lines.append(f"{key}={format_env_value(updates[key])}")
            seen.add(key)
        else:
            updated_lines.append(line)

    missing_keys = [key for key in managed_keys if key in updates and key not in seen]
    if missing_keys:
        if updated_lines and updated_lines[-1].strip():
            updated_lines.append("")
        updated_lines.append("# Setup-managed model/runtime settings")
        for key in missing_keys:
            updated_lines.append(f"{key}={format_env_value(updates[key])}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(updated_lines).rstrip() + "\n", encoding="utf-8")


def provider_preset(name: str) -> ProviderPreset:
    key = (name or "").strip().lower()
    if key not in PROVIDER_PRESETS:
        options = ", ".join(sorted(PROVIDER_PRESETS))
        raise ValueError(f"Unknown provider '{name}'. Expected one of: {options}")
    return PROVIDER_PRESETS[key]


def is_placeholder_secret(value: str) -> bool:
    normalized = (value or "").strip().lower()
    return normalized in {"", "your_api_key_here", "changeme", "change_me"} or "ignore" in normalized


def prompt_text(label: str, default: str = "", *, required: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default:
            return default
        if not required:
            return ""
        print(f"{label} is required.")


def prompt_secret(label: str, default_present: bool, *, required: bool) -> str:
    suffix = " [leave blank to keep existing]" if default_present else ""
    while True:
        value = getpass.getpass(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default_present:
            return ""
        if not required:
            return ""
        print(f"{label} is required.")


def prompt_yes_no(label: str, default: bool = True) -> bool:
    suffix = " [Y/n]" if default else " [y/N]"
    value = input(f"{label}{suffix}: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "1", "true"}


def choose_provider(existing: dict[str, str], value: str | None) -> str:
    if value:
        return provider_preset(value).key

    default = existing.get("APP_MODEL_PROVIDER", "longcat").strip().lower()
    if default not in PROVIDER_PRESETS:
        default = "longcat"

    print("Available model providers:")
    for key, preset in PROVIDER_PRESETS.items():
        marker = " (default)" if key == default else ""
        print(f"  {key}: {preset.label}{marker}")

    while True:
        selected = input(f"Model provider [{default}]: ").strip().lower() or default
        if selected in PROVIDER_PRESETS:
            return selected
        print("Please choose one of: " + ", ".join(PROVIDER_PRESETS))


def build_config_from_args(args: argparse.Namespace, existing: dict[str, str]) -> ModelConfig:
    provider = choose_provider(existing, args.provider) if not args.non_interactive else (
        provider_preset(args.provider or existing.get("APP_MODEL_PROVIDER", "longcat")).key
    )
    preset = provider_preset(provider)

    existing_provider = existing.get("APP_MODEL_PROVIDER", "").strip().lower()
    provider_changed = bool(existing_provider and existing_provider != provider)
    raw_existing_key = existing.get("ANTHROPIC_API_KEY", "")
    existing_key = "" if is_placeholder_secret(raw_existing_key) else raw_existing_key
    existing_base_url = (
        preset.api_base_url if provider_changed else existing.get("ANTHROPIC_API_BASE_URL", preset.api_base_url)
    )
    existing_model = preset.model if provider_changed else existing.get("ANTHROPIC_API_MODEL", preset.model)
    existing_runtime = (
        preset.runtime_provider
        if provider_changed
        else existing.get("APP_AGENT_RUNTIME_PROVIDER", preset.runtime_provider)
    )
    existing_permission = existing.get("APP_AGENT_PERMISSION_MODE", "dontAsk")
    existing_workspace = existing.get("APP_WORKSPACE_ROOT", DEFAULT_WORKSPACE_ROOT)
    existing_frontend = existing.get("NEXT_PUBLIC_API_BASE_URL", "")

    host = args.host or DEFAULT_HOST
    backend_port = args.backend_port or infer_backend_port(existing_frontend) or DEFAULT_BACKEND_PORT
    frontend_port = args.frontend_port or DEFAULT_FRONTEND_PORT

    if args.non_interactive:
        api_key = args.api_key if args.api_key is not None else existing_key
        model = args.model if args.model is not None else existing_model
        api_base_url = args.api_base_url if args.api_base_url is not None else existing_base_url
        runtime_provider = args.runtime_provider if args.runtime_provider is not None else existing_runtime
        permission_mode = args.permission_mode if args.permission_mode is not None else existing_permission
        workspace_root = args.workspace_root if args.workspace_root is not None else existing_workspace
    else:
        model_default = args.model if args.model is not None else existing_model
        base_default = args.api_base_url if args.api_base_url is not None else existing_base_url
        runtime_default = args.runtime_provider if args.runtime_provider is not None else existing_runtime
        permission_default = args.permission_mode if args.permission_mode is not None else existing_permission
        workspace_default = args.workspace_root if args.workspace_root is not None else existing_workspace

        model = prompt_text("Model name", model_default, required=provider != "mock")
        api_base_url = prompt_text("API base URL", base_default, required=provider == "custom")
        api_key_input = prompt_secret(
            "API key",
            bool(existing_key),
            required=preset.requires_api_key and not existing_key,
        )
        api_key = api_key_input or existing_key
        runtime_provider = prompt_text("Agent runtime provider", runtime_default, required=True)
        permission_mode = prompt_text("Permission mode", permission_default, required=True)
        workspace_root = prompt_text("Workspace root", workspace_default, required=True)

    if preset.requires_api_key and not api_key:
        raise RuntimeError("API key is required for provider '" + provider + "'.")
    if provider != "mock" and not model:
        raise RuntimeError("Model name is required for provider '" + provider + "'.")
    if provider == "custom" and not api_base_url:
        raise RuntimeError("API base URL is required for custom provider.")

    return ModelConfig(
        provider=provider,
        api_key=api_key,
        api_base_url=api_base_url,
        model=model,
        runtime_provider=runtime_provider,
        permission_mode=permission_mode,
        workspace_root=workspace_root,
        backend_port=backend_port,
        frontend_port=frontend_port,
        host=host,
    )


def infer_backend_port(api_base_url: str) -> int | None:
    if not api_base_url:
        return None
    try:
        from urllib.parse import urlparse

        parsed = urlparse(api_base_url)
        return parsed.port
    except Exception:
        return None


def configure(args: argparse.Namespace) -> ModelConfig:
    _, existing = read_dotenv(ENV_PATH)
    config = build_config_from_args(args, existing)
    write_dotenv(ENV_PATH, config.to_env_updates())
    print(f"Updated {ENV_PATH}")
    print("Model provider:", config.provider)
    print("Model:", config.model)
    print("Runtime provider:", config.runtime_provider)
    print("Backend API:", config.api_base)
    print("API key: configured" if config.api_key else "API key: not configured")
    return config


def find_python() -> str:
    return sys.executable


def venv_python() -> Path:
    if os.name == "nt":
        return BACKEND_ROOT / ".venv" / "Scripts" / "python.exe"
    return BACKEND_ROOT / ".venv" / "bin" / "python"


def run_checked(command: list[str], *, cwd: Path) -> None:
    print(f"Running in {cwd}: {' '.join(command)}")
    subprocess.run(command, cwd=str(cwd), check=True)


def install_backend() -> None:
    python = find_python()
    venv = venv_python()
    if not venv.exists():
        run_checked([python, "-m", "venv", str(BACKEND_ROOT / ".venv")], cwd=REPO_ROOT)
    run_checked([str(venv), "-m", "pip", "install", "--upgrade", "pip"], cwd=BACKEND_ROOT)
    run_checked([str(venv), "-m", "pip", "install", "-r", "requirements.txt"], cwd=BACKEND_ROOT)


def install_frontend() -> None:
    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("npm was not found. Install Node.js before running setup install.")
    command = [npm, "ci"] if (FRONTEND_ROOT / "package-lock.json").exists() else [npm, "install"]
    run_checked(command, cwd=FRONTEND_ROOT)


def install(args: argparse.Namespace) -> None:
    if not args.skip_backend:
        install_backend()
    if not args.skip_frontend:
        install_frontend()


def is_port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def require_free_ports(host: str, ports: Iterable[tuple[str, int]]) -> None:
    blocked = [f"{name} port {port}" for name, port in ports if not is_port_free(host, port)]
    if blocked:
        raise RuntimeError("Port unavailable: " + ", ".join(blocked))


def load_runtime_env(config: ModelConfig) -> dict[str, str]:
    _, dotenv_values = read_dotenv(ENV_PATH)
    env = os.environ.copy()
    env.update(dotenv_values)
    env.update(config.to_env_updates())
    env["NEXT_PUBLIC_API_BASE_URL"] = config.api_base
    return env


def popen_detached(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
) -> subprocess.Popen:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout = stdout_path.open("ab")
    stderr = stderr_path.open("ab")
    kwargs = {
        "cwd": str(cwd),
        "env": env,
        "stdin": subprocess.DEVNULL,
        "stdout": stdout,
        "stderr": stderr,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        kwargs["start_new_session"] = True
    try:
        return subprocess.Popen(command, **kwargs)
    finally:
        stdout.close()
        stderr.close()


def read_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def write_state(state: dict) -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def wait_for_url(url: str, *, timeout_seconds: int = 20) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return True
        except URLError:
            pass
        except OSError:
            pass
        time.sleep(1)
    return False


def start_services(args: argparse.Namespace) -> None:
    _, existing = read_dotenv(ENV_PATH)
    if not existing:
        raise RuntimeError("No .env found. Run setup configure first.")
    start_args = argparse.Namespace(**vars(args))
    start_args.non_interactive = True
    config = build_config_from_args(start_args, existing)
    require_free_ports(
        config.host,
        [
            ("backend", config.backend_port),
            ("frontend", config.frontend_port),
        ],
    )

    env = load_runtime_env(config)
    python = venv_python() if venv_python().exists() else Path(find_python())
    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("npm was not found. Install Node.js before starting the frontend.")

    backend_log = RUN_DIR / "backend.out.log"
    backend_err = RUN_DIR / "backend.err.log"
    frontend_log = RUN_DIR / "frontend.out.log"
    frontend_err = RUN_DIR / "frontend.err.log"

    backend = popen_detached(
        [
            str(python),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            config.host,
            "--port",
            str(config.backend_port),
        ],
        cwd=BACKEND_ROOT,
        env=env,
        stdout_path=backend_log,
        stderr_path=backend_err,
    )
    frontend = popen_detached(
        [
            npm,
            "run",
            "dev",
            "--",
            "-H",
            config.host,
            "-p",
            str(config.frontend_port),
        ],
        cwd=FRONTEND_ROOT,
        env=env,
        stdout_path=frontend_log,
        stderr_path=frontend_err,
    )

    backend_health_url = f"{config.api_base}/health"
    frontend_url = f"http://{config.host}:{config.frontend_port}"
    state = {
        "started_at": utc_now(),
        "env_path": str(ENV_PATH),
        "backend": {
            "pid": backend.pid,
            "url": config.api_base,
            "health_url": backend_health_url,
            "stdout": str(backend_log),
            "stderr": str(backend_err),
        },
        "frontend": {
            "pid": frontend.pid,
            "url": frontend_url,
            "stdout": str(frontend_log),
            "stderr": str(frontend_err),
        },
    }
    write_state(state)

    backend_ready = wait_for_url(backend_health_url, timeout_seconds=args.wait_seconds)
    print("Backend:", config.api_base)
    print("Backend health:", backend_health_url, "ready" if backend_ready else "starting")
    print("Frontend:", frontend_url)
    print("Runtime metadata:", STATE_PATH)
    print("Logs:", RUN_DIR)


def process_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            check=False,
        )
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def terminate_process(pid: int) -> bool:
    if not process_running(pid):
        return False
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False)
        return True
    try:
        os.killpg(pid, signal.SIGTERM)
    except OSError:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return False
    return True


def stop_services(_: argparse.Namespace) -> None:
    state = read_state()
    if not state:
        print("No setup runtime metadata found.")
        return

    stopped: list[str] = []
    for name in ("frontend", "backend"):
        pid = int((state.get(name) or {}).get("pid") or 0)
        if terminate_process(pid):
            stopped.append(f"{name} ({pid})")
            state.setdefault(name, {})["stopped_at"] = utc_now()
    state["last_stop_at"] = utc_now()
    write_state(state)
    if stopped:
        print("Stopped " + ", ".join(stopped))
    else:
        print("No running setup-managed services found.")


def show_status(_: argparse.Namespace) -> None:
    state = read_state()
    if not state:
        print("No setup runtime metadata found.")
        return
    for name in ("backend", "frontend"):
        item = state.get(name) or {}
        pid = int(item.get("pid") or 0)
        status = "running" if process_running(pid) else "stopped"
        print(f"{name}: {status} pid={pid} url={item.get('url', '')}")


def run_all(args: argparse.Namespace) -> None:
    config = configure(args)
    should_install = args.yes or args.non_interactive
    if not should_install and not args.skip_install:
        should_install = prompt_yes_no("Install backend and frontend dependencies now?", True)
    if not args.skip_install and should_install:
        install(args)
    if not args.skip_start:
        start_services(args)
    else:
        print("Configured .env. Start later with setup start.")
    print("Setup complete.")


def add_config_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider", choices=sorted(PROVIDER_PRESETS))
    parser.add_argument("--model")
    parser.add_argument("--api-key")
    parser.add_argument("--api-base-url")
    parser.add_argument("--runtime-provider", choices=["mock", "claude_agent_sdk"])
    parser.add_argument("--permission-mode", choices=["dontAsk", "manual"])
    parser.add_argument("--workspace-root")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--backend-port", type=int)
    parser.add_argument("--frontend-port", type=int)
    parser.add_argument("--non-interactive", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Configure, install, and start the local business analysis harness.",
    )
    subparsers = parser.add_subparsers(dest="command")

    configure_parser = subparsers.add_parser("configure", help="Create or edit .env model settings.")
    add_config_args(configure_parser)
    configure_parser.set_defaults(func=configure)

    install_parser = subparsers.add_parser("install", help="Install backend and frontend dependencies.")
    install_parser.add_argument("--skip-backend", action="store_true")
    install_parser.add_argument("--skip-frontend", action="store_true")
    install_parser.set_defaults(func=install)

    start_parser = subparsers.add_parser("start", help="Start backend and frontend services.")
    add_config_args(start_parser)
    start_parser.add_argument("--wait-seconds", type=int, default=20)
    start_parser.set_defaults(func=start_services)

    stop_parser = subparsers.add_parser("stop", help="Stop setup-managed services.")
    stop_parser.set_defaults(func=stop_services)

    status_parser = subparsers.add_parser("status", help="Show setup-managed service status.")
    status_parser.set_defaults(func=show_status)

    run_all_parser = subparsers.add_parser("run-all", help="Configure, install, and start services.")
    add_config_args(run_all_parser)
    run_all_parser.add_argument("--yes", action="store_true", help="Accept default yes/no prompts.")
    run_all_parser.add_argument("--skip-install", action="store_true")
    run_all_parser.add_argument("--skip-start", action="store_true")
    run_all_parser.add_argument("--skip-backend", action="store_true")
    run_all_parser.add_argument("--skip-frontend", action="store_true")
    run_all_parser.add_argument("--wait-seconds", type=int, default=20)
    run_all_parser.set_defaults(func=run_all)

    return parser


def normalize_default_command(argv: list[str]) -> list[str]:
    if not argv:
        return ["run-all"]
    commands = {"configure", "install", "start", "stop", "status", "run-all", "-h", "--help"}
    if argv[0] in commands:
        return argv
    return ["run-all", *argv]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(normalize_default_command(list(argv or sys.argv[1:])))
    try:
        args.func(args)
        return 0
    except (RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
