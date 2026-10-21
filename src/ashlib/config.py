"""Local configuration and redaction helpers."""
from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any


SECRET_FIELDS = {"api_key", "authorization", "token"}
PROVIDERS = {
    "openrouter": {"label": "OpenRouter", "base_url": "https://openrouter.ai/api/v1"},
    "xai": {"label": "xAI", "base_url": "https://api.x.ai/v1"},
    "openai": {"label": "OpenAI", "base_url": "https://api.openai.com/v1"},
}


def data_root() -> Path:
    """Return the persistent ash data root, with an override for tests."""
    override = os.environ.get("ASH_AI_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / "Documents" / ".ash-ai"


def config_path() -> Path:
    return data_root() / "config.json"


def plan_path() -> Path:
    return data_root() / "current-plan.json"


def runs_dir() -> Path:
    return data_root() / "runs"


def ensure_data_root() -> Path:
    root = data_root()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        root.chmod(0o700)
    except OSError:
        pass
    return root


def _atomic_write(path: Path, payload: str) -> None:
    ensure_data_root()
    fd, temporary = tempfile.mkstemp(prefix=".ash-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        try:
            os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def write_config(config: dict[str, Any]) -> None:
    required = {"provider", "model", "api_key"}
    if not isinstance(config, dict) or set(config) - (required | {"base_url"}) or not required <= set(config) or not all(isinstance(config[key], str) and config[key].strip() for key in required):
        raise ValueError("configuration must contain non-empty provider, model, and api_key")
    if config["provider"] not in PROVIDERS:
        raise ValueError("configuration has an unsupported provider")
    saved = {key: config[key] for key in required}
    _atomic_write(config_path(), json.dumps(saved, indent=2, sort_keys=True) + "\n")


def load_config(require_key: bool = True) -> dict[str, str]:
    path = config_path()
    if not path.exists():
        raise FileNotFoundError("No configuration found. Run: ash setup")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("Configuration is not valid JSON. Run: ash setup") from error
    if not isinstance(raw, dict):
        raise ValueError("Configuration must be a JSON object. Run: ash setup")
    required = {"provider", "model", "api_key"}
    if not required <= set(raw) or set(raw) - (required | {"base_url"}) or not all(isinstance(raw.get(key), str) and raw[key].strip() for key in {"provider", "model"}):
        raise ValueError("Configuration is incomplete. Run: ash setup")
    if raw["provider"] not in PROVIDERS:
        raise ValueError("Configuration has an unsupported provider. Run: ash setup")
    if require_key and (not isinstance(raw.get("api_key"), str) or not raw["api_key"].strip()):
        raise ValueError("No API key configured. Run: ash setup")
    if not isinstance(raw.get("api_key"), str):
        raise ValueError("Configuration is incomplete. Run: ash setup")
    return {"provider": raw["provider"], "base_url": PROVIDERS[raw["provider"]]["base_url"], "model": raw["model"], "api_key": raw["api_key"]}


def clear_key() -> bool:
    config = load_config(require_key=False)
    config = {"provider": config["provider"], "model": config["model"], "api_key": ""}
    # An empty key intentionally marks setup as incomplete, but retains provider choices.
    _atomic_write(config_path(), json.dumps(config, indent=2, sort_keys=True) + "\n")
    return True


def redact(value: Any) -> Any:
    """Recursively redact conventional secret fields before display or logging."""
    if isinstance(value, dict):
        return {key: "[REDACTED]" if key.lower() in SECRET_FIELDS else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def redact_text(text: str, config: dict[str, str] | None = None) -> str:
    if config and config.get("api_key"):
        return text.replace(config["api_key"], "[REDACTED]")
    return text
