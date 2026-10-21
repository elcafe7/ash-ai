"""Local environment checks suitable for a-Shell."""
from __future__ import annotations

import os
import shutil
import sys
import os
from pathlib import Path

from .config import data_root, load_config


def capability_profile() -> str:
    return "a-Shell iOS; Python standard library only; pure-Python packages only; use pkg for supported WASM commands; no apt/brew/sudo/services."


def diagnose() -> list[str]:
    findings: list[str] = []
    if sys.version_info < (3, 8):
        findings.append("FAIL: Python 3.8 or newer is required.")
    else:
        findings.append("OK: Python " + sys.version.split()[0])
    if shutil.which("curl"):
        findings.append("OK: curl is available.")
    else:
        findings.append("WARN: curl is not on PATH; urllib is used for requests.")
    root = data_root()
    app = root / "app"
    launcher = Path.home() / "Documents" / "bin" / "ash"
    if app.is_dir() and (app / "src" / "ashlib").is_dir():
        findings.append("OK: installed app files are present: " + str(app))
    else:
        findings.append("FAIL: installed app files are missing or incomplete: " + str(app))
    if launcher.is_file() and os.access(launcher, os.X_OK):
        findings.append("OK: ash launcher is executable: " + str(launcher))
    else:
        findings.append("FAIL: ash launcher is missing or not executable: " + str(launcher))
    if str(launcher.parent) in os.environ.get("PATH", "").split(os.pathsep):
        findings.append("OK: launcher directory is on PATH.")
    else:
        findings.append("FAIL: launcher directory is not on PATH.")
    profile = Path.home() / ".profile"
    try:
        profile_text = profile.read_text(encoding="utf-8")
        start = profile_text.count('# ash-ai PATH BEGIN')
        end = profile_text.count('# ash-ai PATH END')
        if start == 1 and end == 1 and profile_text.index('# ash-ai PATH BEGIN') < profile_text.index('# ash-ai PATH END'):
            findings.append("OK: marked ash PATH block is present in " + str(profile))
        else:
            findings.append("FAIL: marked ash PATH block is missing or malformed in " + str(profile))
    except OSError:
        findings.append("FAIL: cannot read profile for marked ash PATH block: " + str(profile))
    try:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        probe = root / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        findings.append("OK: data directory is writable: " + str(root))
    except OSError:
        findings.append("FAIL: data directory is not writable: " + str(root))
    try:
        load_config()
        findings.append("OK: configuration is valid.")
    except FileNotFoundError:
        findings.append("WARN: no API configuration; run ash setup.")
    except ValueError:
        findings.append("FAIL: configuration is malformed; run ash setup.")
    return findings


def failed(findings: list[str]) -> bool:
    return any(item.startswith("FAIL:") for item in findings)
