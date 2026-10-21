"""Positive allowlist for commands that may run in a-Shell."""
from __future__ import annotations

import re
import shlex


RISKS = {"read_only", "network", "writes_files", "deletes_files", "elevated_risk"}
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
PACKAGE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
# Verified a-Shell WebAssembly packages supported by the v1 catalog. Do not
# claim arbitrary Unix programs are installable through a-Shell's pkg command.
A_SHELL_PKG_CATALOG = frozenset({"zip", "unzip", "xz", "ffmpeg"})


def validate_command(command: str, risk: str | None = None) -> list[str]:
    """Return argv for an explicitly supported single-process operation."""
    if not isinstance(command, str) or not command.strip() or len(command) > 1000 or CONTROL.search(command):
        raise ValueError("command must be a non-empty string without control characters")
    try:
        argv = shlex.split(command, posix=True)
    except ValueError as error:
        raise ValueError("command is not a valid argument list") from error
    if not argv or any(any(c in arg for c in "|;&<>`$") for arg in argv):
        raise ValueError("command contains a shell operator not allowed")
    program, args = argv[0], argv[1:]
    valid = False
    if program == "pkg":
        valid = args == ["--version"] or (len(args) == 2 and args[0] == "install" and args[1] in A_SHELL_PKG_CATALOG and risk == "network")
    elif program in {"pip", "pip3"}:
        valid = args == ["--version"] or (len(args) == 2 and args[0] == "install" and PACKAGE.fullmatch(args[1]) and risk == "network")
    elif program == "python3":
        valid = args == ["--version"] or (len(args) == 4 and args[:3] == ["-m", "pip", "install"] and PACKAGE.fullmatch(args[3]) and risk == "network")
    elif program == "help":
        valid = args == ["-l"]
    elif program == "which":
        valid = len(args) == 1 and SAFE_NAME.fullmatch(args[0]) is not None
    elif program == "command":
        valid = len(args) == 2 and args[0] == "-v" and SAFE_NAME.fullmatch(args[1]) is not None
    elif program == "pwd":
        valid = not args
    elif program == "ls":
        valid = not args or (len(args) == 1 and not args[0].startswith("/") and ".." not in args[0].split("/"))
    if not valid:
        raise ValueError("unsupported command")
    return argv
