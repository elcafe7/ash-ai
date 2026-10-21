"""Stable terminal rendering for plans."""
from __future__ import annotations

from typing import Any


def render_plan(plan: dict[str, Any]) -> str:
    lines = [f"Plan: {plan['summary']}"]
    if plan["status"] == "unsupported":
        return "\n".join(lines + [f"Unsupported: {plan['reason']}"])
    for number, step in enumerate(plan["steps"], start=1):
        lines.extend((
            f"{number}. {step['command']}",
            f"   Why: {step['why']}",
            f"   Risk: {step['risk']}",
            f"   Expected: {step['expected']}",
        ))
    lines.extend(("", "Run this exact plan: ash run", "Discard it:            ash discard"))
    return "\n".join(lines)
