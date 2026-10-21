"""Deterministic, offline diagnostics for ash-ai and a-Shell setup."""
from __future__ import annotations

from pathlib import Path

from .config import load_config, redact_text, runs_dir


SIGNATURES = (
    ("command not found", "A command is unavailable. Run `help -l | grep <command>` in a-Shell; use `pkg install <command>` only when a-Shell provides it."),
    ("no module named", "A Python module is missing. a-Shell can install only pure-Python packages; native-extension packages will not work."),
    ("permission denied", "A file permission or iOS sandbox restriction blocked this action. Use a location under ~/Documents, ~/Library, or ~/tmp."),
    ("no such file or directory", "A referenced path does not exist. Check the path and use `pwd` plus `ls` before retrying."),
    ("network is unreachable", "Network access is unavailable. Verify Wi-Fi/cellular access and retry; ash will not retry automatically."),
    ("temporary failure in name resolution", "DNS lookup failed. Verify network access and retry."),
    ("http 401", "The provider rejected authentication. Run `ash setup` and replace the API key."),
    ("http 429", "The provider rate-limited the request. Wait, check account limits, then retry manually."),
)


def latest_log() -> Path | None:
    directory = runs_dir()
    if not directory.is_dir():
        return None
    logs = sorted(directory.glob("*.log"))
    return logs[-1] if logs else None


def debug_report() -> list[str]:
    """Return safe diagnostics only; this function never calls a provider or shell."""
    report = ["Offline debugger: no AI/API request was made."]
    try:
        config = load_config(require_key=False)
        report.append("OK: saved provider is " + config["provider"] + "; API key is " + ("set." if config["api_key"] else "not set."))
    except (FileNotFoundError, ValueError):
        report.append("WARN: provider setup is missing or malformed; run `ash setup`.")
        config = None
    log = latest_log()
    if log is None:
        report.append("INFO: no previous run log exists.")
        return report
    report.append("Latest run log: " + str(log))
    try:
        content = redact_text(log.read_text(encoding="utf-8", errors="replace").lower(), config)
    except OSError:
        report.append("WARN: the latest run log could not be read.")
        return report
    matches = [advice for signature, advice in SIGNATURES if signature in content]
    if matches:
        report.extend("Diagnosis: " + advice for advice in matches)
    else:
        report.append("INFO: no known failure signature was found. Review the exact command and output in the log; ash did not retry it.")
    return report
