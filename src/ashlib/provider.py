"""Minimal OpenAI-compatible chat-completions client."""
from __future__ import annotations

import json
import socket
from typing import Any, Callable
from urllib import error, request

from .config import PROVIDERS, redact_text


SYSTEM_PROMPT = """You produce a command plan for a-Shell on iOS. Return ONLY one JSON object matching this exact schema: {schema_version: 1, summary: string, status: ready|unsupported, reason: string|null, steps: [{command: string, why: string, risk: read_only|network|writes_files|deletes_files|elevated_risk, expected: string}]}. The shell is not Linux: never propose apt, brew, apk, sudo, Docker, services, or native Python extensions. Prefer a-Shell pkg install for known commands and pure-Python pip packages only when necessary. Use 1-12 minimal steps. Never use pipes, redirections, command substitution, shell operators, newlines, wrappers, or encoded payloads. Use status unsupported with a concise reason if no safe a-Shell path exists. The user must approve every risky command, so do not execute or claim that commands executed."""


class ProviderError(RuntimeError):
    pass


def _endpoint(base_url: str) -> str:
    return base_url.rstrip("/") + "/chat/completions"


def request_plan(config: dict[str, str], task: str, opener: Callable[..., Any] = request.urlopen, timeout: int = 45) -> dict[str, Any]:
    provider = config.get("provider")
    if provider not in PROVIDERS:
        raise ProviderError("Configuration has an unsupported provider.")
    body = {
        "model": config["model"],
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Task: " + task},
        ],
    }
    encoded = json.dumps(body).encode("utf-8")
    req = request.Request(
        _endpoint(PROVIDERS[provider]["base_url"]),
        data=encoded,
        headers={"Authorization": "Bearer " + config["api_key"], "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with opener(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        raise ProviderError(f"API request failed with HTTP {exc.code}.") from exc
    except (error.URLError, socket.timeout, TimeoutError) as exc:
        raise ProviderError("API request failed: network error or timeout.") from exc
    try:
        payload = json.loads(raw)
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ProviderError("API returned an invalid chat-completions response.") from exc
    if not isinstance(content, str) or content.lstrip().startswith("```"):
        raise ProviderError("API response must be plain JSON without Markdown fences.")
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        safe = redact_text(content[:160], config)
        raise ProviderError(f"API response was not valid plan JSON: {safe!r}") from exc
