"""Sequential command execution with a deliberate confirmation gate."""
from __future__ import annotations

import datetime as dt
import os
import shlex
import stat
import subprocess
from pathlib import Path
from typing import Any, Callable

from .config import ensure_data_root, load_config, redact_text, runs_dir
from .plan import validate_plan
from .safety import validate_command


Confirmation = Callable[[str], str]


def _log_path() -> Path:
    ensure_data_root()
    directory = runs_dir()
    directory.mkdir(mode=0o700, exist_ok=True)
    try:
        directory.chmod(0o700)
    except OSError:
        pass
    stem = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    for suffix in range(10000):
        path = directory / (stem + (f"-{suffix}" if suffix else "") + ".log")
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, stat.S_IRUSR | stat.S_IWUSR)
            os.close(fd)
            return path
        except FileExistsError:
            continue
    raise OSError("could not allocate a unique run log")


def execute_plan(plan: dict[str, Any], confirm: Confirmation = input, runner: Callable[..., Any] = subprocess.run) -> tuple[int, Path]:
    validate_plan(plan)
    if plan["status"] != "ready":
        raise ValueError("Unsupported plans cannot run.")
    try:
        config = load_config()
    except (FileNotFoundError, ValueError):
        config = None
    log = _log_path()
    with log.open("w", encoding="utf-8") as handle:
        for number, step in enumerate(plan["steps"], start=1):
            answer = confirm(f"Run step {number} ({step['risk']})? Type yes to continue: ")
            if answer != "yes":
                handle.write(f"Step {number} declined.\n")
                return 1, log
            command = step["command"]
            display_command = redact_text(command, config)
            print(f"$ {display_command}")
            handle.write(f"$ {display_command}\n")
            try:
                result = runner(validate_command(command, step["risk"]), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
                output = redact_text(result.stdout or "", config)
            except OSError as exc:
                output = redact_text(str(exc), config)
                handle.write(output + "\n")
                return 1, log
            handle.write(output)
            if output:
                print(output, end="" if output.endswith("\n") else "\n")
            if output and not output.endswith("\n"):
                handle.write("\n")
            if result.returncode != 0:
                handle.write(f"Step {number} failed with exit code {result.returncode}.\n")
                return result.returncode or 1, log
    return 0, log
