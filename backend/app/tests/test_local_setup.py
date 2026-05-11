import argparse
import importlib.util
import sys
from pathlib import Path


def load_local_setup():
    module_path = Path(__file__).resolve().parents[3] / "scripts" / "local_setup.py"
    spec = importlib.util.spec_from_file_location("local_setup", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_write_dotenv_preserves_unrelated_keys(tmp_path):
    local_setup = load_local_setup()
    env_path = tmp_path / ".env"
    env_path.write_text(
        "UNRELATED=keep\n"
        "ANTHROPIC_API_MODEL=old-model\n"
        "# comment stays\n",
        encoding="utf-8",
    )

    local_setup.write_dotenv(
        env_path,
        {
            "ANTHROPIC_API_MODEL": "new-model",
            "ANTHROPIC_API_KEY": "secret-value",
            "APP_MODEL_PROVIDER": "custom",
        },
    )

    content = env_path.read_text(encoding="utf-8")
    assert "UNRELATED=keep" in content
    assert "# comment stays" in content
    assert "ANTHROPIC_API_MODEL=new-model" in content
    assert "ANTHROPIC_API_KEY=secret-value" in content
    assert "APP_MODEL_PROVIDER=custom" in content

    _, values = local_setup.read_dotenv(env_path)
    assert values["UNRELATED"] == "keep"
    assert values["ANTHROPIC_API_MODEL"] == "new-model"


def test_provider_presets_define_expected_runtime_defaults():
    local_setup = load_local_setup()

    longcat = local_setup.provider_preset("longcat")
    assert longcat.runtime_provider == "claude_agent_sdk"
    assert longcat.model == "LongCat-Flash-Chat"
    assert longcat.api_base_url == "https://api.longcat.chat/anthropic"

    mock = local_setup.provider_preset("mock")
    assert mock.runtime_provider == "mock"
    assert mock.requires_api_key is False


def test_non_interactive_config_uses_provider_defaults():
    local_setup = load_local_setup()
    args = argparse.Namespace(
        provider="mock",
        model=None,
        api_key=None,
        api_base_url=None,
        runtime_provider=None,
        permission_mode=None,
        workspace_root=None,
        host="127.0.0.1",
        backend_port=18082,
        frontend_port=3011,
        non_interactive=True,
    )

    config = local_setup.build_config_from_args(args, {})
    updates = config.to_env_updates()

    assert updates["APP_MODEL_PROVIDER"] == "mock"
    assert updates["APP_AGENT_RUNTIME_PROVIDER"] == "mock"
    assert updates["ANTHROPIC_API_KEY"] == ""
    assert updates["NEXT_PUBLIC_API_BASE_URL"] == "http://127.0.0.1:18082"


def test_provider_change_uses_new_provider_defaults():
    local_setup = load_local_setup()
    args = argparse.Namespace(
        provider="anthropic",
        model=None,
        api_key="real-key",
        api_base_url=None,
        runtime_provider=None,
        permission_mode=None,
        workspace_root=None,
        host="127.0.0.1",
        backend_port=None,
        frontend_port=None,
        non_interactive=True,
    )
    existing = {
        "APP_MODEL_PROVIDER": "longcat",
        "ANTHROPIC_API_BASE_URL": "https://api.longcat.chat/anthropic",
        "ANTHROPIC_API_MODEL": "LongCat-Flash-Chat",
    }

    config = local_setup.build_config_from_args(args, existing)

    assert config.provider == "anthropic"
    assert config.api_base_url == ""
    assert config.model == "claude-opus-4-5-20250501"
