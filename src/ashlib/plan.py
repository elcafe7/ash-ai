"""Plan validation and current-plan persistence."""
from __future__ import annotations

import json
from typing import Any

from . import SCHEMA_VERSION
from .config import _atomic_write, plan_path
from .safety import RISKS, validate_command


PLAN_FIELDS = {"schema_version", "summary", "status", "reason", "steps"}
STEP_FIELDS = {"command", "why", "risk", "expected"}


def _string(value: Any, name: str, allow_null: bool = False) -> None:
    if allow_null and value is None:
        return
    from .safety import CONTROL
    if not isinstance(value, str) or not value.strip() or len(value) > 1000 or CONTROL.search(value):
        raise ValueError(f"{name} must be a non-empty string no longer than 1000 characters")


def validate_plan(plan: Any) -> dict[str, Any]:
    if not isinstance(plan, dict) or set(plan) != PLAN_FIELDS:
        raise ValueError("plan must have exactly the supported schema fields")
    if plan["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported plan schema version")
    _string(plan["summary"], "summary")
    if plan["status"] not in {"ready", "unsupported"}:
        raise ValueError("plan status must be ready or unsupported")
    _string(plan["reason"], "reason", allow_null=True)
    steps = plan["steps"]
    if not isinstance(steps, list):
        raise ValueError("plan steps must be a list")
    if plan["status"] == "unsupported":
        if steps or plan["reason"] is None:
            raise ValueError("unsupported plans require a reason and no steps")
        return plan
    if plan["reason"] is not None or not 1 <= len(steps) <= 12:
        raise ValueError("ready plans require 1-12 steps and a null reason")
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict) or set(step) != STEP_FIELDS:
            raise ValueError(f"step {index} has unsupported fields")
        _string(step["command"], f"step {index} command")
        _string(step["why"], f"step {index} why")
        _string(step["expected"], f"step {index} expected")
        if step["risk"] not in RISKS:
            raise ValueError(f"step {index} has an invalid risk")
        validate_command(step["command"], step["risk"])
    return plan


def save_current(plan: dict[str, Any]) -> None:
    validate_plan(plan)
    path = plan_path()
    _atomic_write(path, json.dumps(plan, indent=2, sort_keys=True) + "\n")


def load_current() -> dict[str, Any]:
    path = plan_path()
    if not path.exists():
        raise FileNotFoundError("No saved plan. Start with: ash <task>")
    try:
        return validate_plan(json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as error:
        raise ValueError("Saved plan is corrupted. Run: ash discard") from error


def discard_current() -> bool:
    path = plan_path()
    if not path.exists():
        return False
    path.unlink()
    return True
