"""CLI wiring for ash-ai."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Callable

from . import SCHEMA_VERSION, __version__
from .config import PROVIDERS, clear_key, config_path, load_config, plan_path, write_config
from .doctor import diagnose, failed
from .debugger import debug_report
from .executor import execute_plan
from .plan import discard_current, load_current, save_current, validate_plan
from .provider import ProviderError, request_plan
from .render import render_plan
from .safety import PACKAGE


def _yes(prompt: str, reader: Callable[[str], str] = input) -> bool:
    return reader(prompt) == "yes"


def _setup() -> int:
    print("Choose your API provider:")
    provider_names = list(PROVIDERS)
    for number, name in enumerate(provider_names, start=1):
        print(f"  {number}. {PROVIDERS[name]['label']}")
    selected = input("Provider [1-3]: ").strip()
    try:
        provider = provider_names[int(selected) - 1]
    except (ValueError, IndexError):
        print("Choose 1, 2, or 3.", file=sys.stderr)
        return 2
    preset = PROVIDERS[provider]
    print("Selected: " + preset["label"])
    print("Endpoint: " + preset["base_url"])
    model = input("Model: ").strip()
    # getpass can deadlock under a-Shell's terminal bridge. Use normal input
    # deliberately instead of attempting a hidden prompt that may freeze.
    print("Note: a-Shell cannot reliably hide this prompt; paste the key, then avoid sharing terminal screenshots/history.", file=sys.stderr)
    key = input("API key: ").strip()
    if not model or not key:
        print("Model and API key are required.", file=sys.stderr)
        return 2
    if config_path().exists() and not _yes("Replace existing configuration? Type yes to continue: "):
        print("Configuration unchanged.")
        return 1
    write_config({"provider": provider, "base_url": preset["base_url"], "model": model, "api_key": key})
    print("Configuration saved at " + str(config_path()))
    print("Remove the stored key later with: ash key clear")
    return 0


def _status() -> int:
    try:
        config = load_config(require_key=False)
        key_state = "set" if config["api_key"] else "not set"
        print("Provider: " + PROVIDERS[config["provider"]]["label"])
        print("Base URL: " + config["base_url"])
        print("Model: " + config["model"])
    except (FileNotFoundError, ValueError):
        key_state = "not set"
        print("Configuration: unavailable")
    print("API key: " + key_state)
    print("Config path: " + str(config_path()))
    return 0


def _plan(task: str) -> int:
    if not task.strip():
        print("Provide a task, for example: ash \"install jq\"", file=sys.stderr)
        return 2
    # The most common a-Shell task does not need a model: turn an exact simple
    # package request into the same constrained plan the model may produce.
    words = task.split()
    if len(words) == 2 and words[0].lower() == "install" and PACKAGE.fullmatch(words[1]):
        plan = {
            "schema_version": SCHEMA_VERSION,
            "summary": "Install a-Shell package " + words[1] + ".",
            "status": "ready",
            "reason": None,
            "steps": [{
                "command": "pkg install " + words[1],
                "why": "Install the requested a-Shell command package.",
                "risk": "network",
                "expected": "a-Shell reports the package installation result.",
            }],
        }
        if plan_path().exists() and not _yes("Replace the existing saved plan? Type yes to continue: "):
            print("Plan not saved.")
            return 1
        save_current(plan)
        print(render_plan(plan))
        return 0
    try:
        config = load_config()
        plan = validate_plan(request_plan(config, task))
    except (FileNotFoundError, ValueError, ProviderError) as error:
        print("ash: " + str(error), file=sys.stderr)
        return 1
    if plan_path().exists() and not _yes("Replace the existing saved plan? Type yes to continue: "):
        print("Plan not saved.")
        return 1
    save_current(plan)
    print(render_plan(plan))
    return 0


def _run() -> int:
    try:
        code, log = execute_plan(load_current())
    except (FileNotFoundError, ValueError) as error:
        print("ash: " + str(error), file=sys.stderr)
        return 1
    print("Run log: " + str(log))
    if code:
        print("Plan stopped. Run ash explain for the next diagnostic action.", file=sys.stderr)
    return code


def _discard() -> int:
    if not plan_path().exists():
        print("No saved plan.")
        return 0
    if not _yes("Discard the current plan? Type yes to continue: "):
        print("Plan retained.")
        return 1
    discard_current()
    print("Plan discarded.")
    return 0


def _explain() -> int:
    print("Inspect the latest run log, correct the task or setup, then request a new plan. ash does not send logs to an API automatically.")
    return 0


def _doctor() -> int:
    findings = diagnose()
    print("\n".join(findings))
    return 1 if failed(findings) else 0


def _debug() -> int:
    print("\n".join(debug_report()))
    return 0


def _menu() -> int:
    """Small terminal navigation menu shown when ash starts with no arguments."""
    while True:
        print("\nash — a-Shell AI helper")
        try:
            config = load_config(require_key=False)
            print("Provider: " + PROVIDERS[config["provider"]]["label"] + " | model: " + config["model"])
        except (FileNotFoundError, ValueError):
            print("No provider configured.")
        print("1. Ask for a command plan")
        print("2. Set or change API provider")
        print("3. Status")
        print("4. Doctor")
        print("5. Offline debugger")
        print("q. Quit")
        choice = input("Choose: ").strip().lower()
        if choice == "1":
            task = input("What do you want to do in a-Shell? ").strip()
            return _plan(task)
        if choice == "2":
            return _setup()
        if choice == "3":
            _status()
            continue
        if choice == "4":
            _doctor()
            continue
        if choice == "5":
            _debug()
            continue
        if choice in {"q", "quit", "exit"}:
            return 0
        print("Choose 1, 2, 3, 4, 5, or q.", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ash", description="Safe BYOK AI helper for a-Shell")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("setup")
    sub.add_parser("status")
    sub.add_parser("plan")
    sub.add_parser("run")
    sub.add_parser("discard")
    sub.add_parser("explain")
    sub.add_parser("doctor")
    sub.add_parser("debug", help="offline diagnosis of local setup and last run")
    sub.add_parser("version")
    key = sub.add_parser("key")
    key_sub = key.add_subparsers(dest="key_command")
    key_sub.add_parser("clear")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    known = {"setup", "status", "plan", "run", "discard", "explain", "doctor", "debug", "version", "key", "-h", "--help"}
    if argv and argv[0].startswith("-"):
        print(f"{parser.prog}: error: unrecognized arguments: {argv[0]}", file=sys.stderr)
        return 2
    if argv and argv[0] not in known:
        return _plan(" ".join(argv))
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code or 0)
    try:
        return _dispatch(args, parser)
    except (EOFError, KeyboardInterrupt):
        print("\nash: cancelled.", file=sys.stderr)
        return 130


def _dispatch(args, parser) -> int:
    if not args.command:
        return _menu()
    if args.command == "setup": return _setup()
    if args.command == "status": return _status()
    if args.command == "plan":
        try: print(render_plan(load_current())); return 0
        except (FileNotFoundError, ValueError) as error: print("ash: " + str(error), file=sys.stderr); return 1
    if args.command == "run": return _run()
    if args.command == "discard": return _discard()
    if args.command == "explain": return _explain()
    if args.command == "doctor": return _doctor()
    if args.command == "debug": return _debug()
    if args.command == "version": print(f"ash {__version__} (plan schema {SCHEMA_VERSION})"); return 0
    if args.command == "key":
        if args.key_command != "clear": parser.error("key requires: clear")
        if not _yes("Delete the stored API key? Type yes to continue: "): print("Key retained."); return 1
        try: clear_key(); print("API key cleared."); return 0
        except (FileNotFoundError, ValueError) as error: print("ash: " + str(error), file=sys.stderr); return 1
    parser.error("unsupported command")
    return 2
