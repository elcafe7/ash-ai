# a-Shell AI Helper (`ash`): Implementation Specification

## 1. Product statement

`ash` is a BYOK, command-line AI helper installed inside **a-Shell Beta** on
iOS. It turns a plain-language task into a small, reviewable command plan that
is compatible with a-Shell, then executes only the plan the user explicitly
approves.

Install from an extracted release directory:

```sh
cd /path/to/extracted/ash-ai-release
sh ./install.sh
ash setup
ash "install a JSON formatter"
ash run
```

## 2. Non-goals

- Do not build a separate native iOS app in v1.
- Do not execute a model response immediately or implicitly.
- Do not support installing native Python extensions.
- Do not claim arbitrary Unix/Linux compatibility.
- Do not require `pip`, Node, Homebrew, a compiler, or any dependency beyond
  a-Shell's included `python3`, POSIX shell, and `curl`.
- Do not transmit terminal history, file contents, API keys, or environment
  variables unless the user deliberately supplies them as task input.

## 3. Platform contract

The implementation targets a-Shell Beta and must follow these constraints:

- Persistent user files belong under `~/Documents`; use
  `~/Documents/.ash-ai/` as the data root.
- Executable entry points belong under `~/Documents/bin/`.
- `~/.profile` is the supported startup customization point. The installer
  must add `~/Documents/bin` to `PATH` idempotently.
- Python additions must be standard-library only in v1. a-Shell supports
  `pip` only for pure-Python packages and cannot load Python dynamic libraries.
- Prefer `pkg install <name>` for known a-Shell WASM command packages. Do not
  suggest `apt`, `brew`, `sudo`, Docker, daemon/service management, or Linux
  package-manager commands.
- The product may use network access only after the user invokes an AI command
  or installer action which needs it.

## 4. User experience

### 4.1 First run

Running `ash` with no arguments opens a terminal navigation menu. Its initial
state says `No provider configured` and offers `Set or change API provider`.
Once configured, it displays the saved provider and model and offers a command
plan prompt, provider setup, status, and doctor.

`ash setup` interactively asks for:

1. Provider: `OpenRouter`, `xAI`, or `OpenAI`.
2. Model identifier; no hard-coded model default is required.
3. API key, entered without echo where the terminal supports it.

It saves the selected provider as the default for future sessions, writes a
local configuration file and prints the exact key location and
the command to erase it. It must never print the key.

Provider endpoint presets are fixed in the application: OpenRouter
`https://openrouter.ai/api/v1`, xAI `https://api.x.ai/v1`, and OpenAI
`https://api.openai.com/v1`.

### 4.2 Planning

`ash <task>` sends a minimal capability profile and the user task to the
configured API. It displays a plan but does **not** execute it.

Example display:

```text
Plan saved: plan-20261021T153600Z-a1b2c3
1. pkg install jq
   Install a-Shell's jq-compatible command package. Network download.
2. jq --version
   Verify installation. Read-only.

Run this exact plan: ash run
Discard it:            ash discard
```

### 4.3 Execution

`ash run` executes the current saved plan one command at a time. Every
executable model-generated command is displayed and requires the literal `yes`
confirmation, regardless of its risk label.

On failure, stop immediately, preserve output in the run log, and print the
failing step number plus `ash explain` as the next recovery action.

## 5. Command interface

| Command | Required behavior |
|---|---|
| `ash` | Open the navigation menu; shows the saved provider/model or requests provider configuration. |
| `ash setup` | Choose and save OpenRouter, xAI, or OpenAI configuration after confirmation. |
| `ash status` | Print provider name/base URL, model, config path, and whether a key is set; never print the key. |
| `ash <task…>` | Request, validate, display, and save one plan. |
| `ash plan` | Print the current plan exactly as saved. |
| `ash run` | Execute the current plan with confirmation for every step. |
| `ash discard` | Remove current plan after confirmation. |
| `ash explain` | Show the last run failure and a safe diagnostic prompt; no API call unless `--ask` is added later. |
| `ash doctor` | Check Python, curl, writable data directories, PATH installation, config validity, and a-Shell compatibility assumptions. |
| `ash debug` | Offline-only diagnosis of saved setup and the latest redacted run log; never calls an API or executes a command. |
| `ash key clear` | Delete only the stored API key after confirmation. |
| `ash version` | Print semantic version and schema version. |

Unknown flags and commands must return a nonzero exit code with concise help.

## 6. Files and permissions

```text
~/Documents/
  bin/ash                         # executable launcher
  .ash-ai/
    config.json                   # provider id, model, plaintext API key
    current-plan.json             # validated but unexecuted plan
    runs/<run-id>.log             # command output; no API keys
    install.json                  # version and installer metadata
```

- Create directories with mode `0700` where supported.
- Create files with mode `0600` where supported.
- Never include `Authorization`, API keys, or raw request headers in logs.
- The API key is plaintext in `~/Documents/.ash-ai/config.json`, inside the
  a-Shell Documents container. It is not stored in iOS Keychain.
- Before overwriting a configuration or plan, require confirmation or create a
  timestamped backup under `.ash-ai/` with secret fields redacted.

## 7. Provider protocol

Use Python standard library `urllib.request`; do not add `requests`.

### 7.1 Request

Send a `POST` to `${base_url}/chat/completions` with:

- `Authorization: Bearer <api_key>`
- JSON body containing `model`, `messages`, `temperature: 0`, and an explicit
  instruction to return **only** the JSON plan schema below.

The system prompt must state the platform contract from section 3, prohibit
shell wrappers/encoded payloads, require a minimal plan, and tell the model to
return an `unsupported` plan when no safe a-Shell path exists.

### 7.2 Response handling

Accept only `choices[0].message.content` that parses as JSON and validates
against the local schema. Refuse markdown fences, prose before/after JSON,
unknown fields, plans over 12 steps, and commands containing newline or NUL.

HTTP/API errors must show the HTTP status and a redacted diagnostic. Never
display request headers or body fields containing the key.

## 8. Plan schema (v1)

```json
{
  "schema_version": 1,
  "summary": "Install and verify jq.",
  "status": "ready",
  "reason": null,
  "steps": [
    {
      "command": "pkg install jq",
      "why": "Install a-Shell's packaged jq command.",
      "risk": "network",
      "expected": "The package installer reports success."
    }
  ]
}
```

Rules:

- `status` is `ready` or `unsupported`.
- An `unsupported` plan has no steps and a nonempty `reason`.
- A `ready` plan has 1–12 steps.
- `risk` is exactly one of `read_only`, `network`, `writes_files`,
  `deletes_files`, `elevated_risk`.
- Every string is nonempty after trimming and at most 1,000 characters.
- Commands must be a single line and must not contain control characters.
- The validator rejects known incompatible tokens: `apt`, `apt-get`, `apk`,
  `brew`, `sudo`, `yum`, `dnf`, `pacman`, `systemctl`, `launchctl`, `docker`.
- The validator rejects shell-control characters in v1: backticks, `$(`,
  `>`, `>>`, `<`, `&&`, `||`, `;`, and newline. Pipes are rejected in v1 too.
- Permit a narrow command grammar first: command name plus quoted/unquoted
  arguments. Expanding it requires a schema version change and security review.

The validator is a safety boundary, not a substitute for user confirmation.

## 9. Repository layout

```text
ash-ai/
  SPEC.md
  README.md
  install.sh
  uninstall.sh
  src/
    ash.py
    ashlib/
      __init__.py
      cli.py
      config.py
      doctor.py
      executor.py
      plan.py
      provider.py
      render.py
      safety.py
  tests/
    test_config.py
    test_plan.py
    test_safety.py
    test_provider.py
    test_executor.py
  fixtures/
    valid-plan.json
    unsupported-plan.json
    malformed-response.txt
```

The launcher must import only from the installed local `src/` tree. No package
installation process is needed.

## 10. Independent agent work packets

Each packet can be assigned to a low-reasoning coding agent. It must change
only its listed files, run its listed tests, and report the exact files changed.
An agent must not redesign the schema or weaken the safety rules.

### WP-01 — Repository skeleton and launcher

**Files:** `README.md`, `install.sh`, `uninstall.sh`, `src/ash.py`,
`src/ashlib/__init__.py`

**Task:** Create the file layout and a POSIX installer. It must install only
from an extracted release tree, stage and verify the source before replacing
`~/Documents/.ash-ai/app`, create `~/Documents/bin/ash` without overwriting an
unrelated launcher, bound retained app backups, and add a marked PATH block to
`~/.profile` idempotently. Uninstall must require the ash install sentinel and
remove only `~/Documents/.ash-ai` plus its marked PATH block.

**Acceptance:**

```sh
sh -n install.sh
sh -n uninstall.sh
python3 src/ash.py version
```

Installer must not invoke pip or pkg and must not make a network request.

### WP-02 — CLI routing and help

**Files:** `src/ash.py`, `src/ashlib/cli.py`, `tests/test_cli.py`

**Task:** Implement `argparse` routing for every section-5 command. Each
handler can temporarily return a clear “not implemented” error except `version`
and help. Preserve task text after `ash` as one task string.

**Acceptance:**

```sh
python3 src/ash.py version
python3 src/ash.py --help
python3 src/ash.py unknown; test $? -ne 0
```

### WP-03 — Configuration and secret redaction

**Files:** `src/ashlib/config.py`, `tests/test_config.py`

**Task:** Implement paths, atomic JSON writes, config loading, setup input
helpers, `status` data, and `key clear`. Use `getpass.getpass` when available;
fall back to input with a visible warning. Implement recursive redaction for
fields named `api_key`, `authorization`, or `token`.

**Acceptance:** tests prove a key round-trips locally, never occurs in `status`,
and is absent from a redacted serialized object.

### WP-04 — Plan schema and validator

**Files:** `src/ashlib/plan.py`, `src/ashlib/safety.py`, `tests/test_plan.py`,
`tests/test_safety.py`, `fixtures/valid-plan.json`, `fixtures/unsupported-plan.json`

**Task:** Implement the exact section-8 schema and safety rejection rules.
Do not use third-party schema libraries.

**Acceptance:** unit tests accept both fixtures and reject every forbidden
token/control operator, unknown object field, wrong risk, oversized plan, and
unsupported plan with steps.

### WP-05 — OpenAI-compatible provider

**Files:** `src/ashlib/provider.py`, `tests/test_provider.py`,
`fixtures/malformed-response.txt`

**Task:** Implement request construction and response extraction using only
`urllib`. Inject the HTTP opener for tests. Ensure all exception strings and
debug output are redacted.

**Acceptance:** mocked tests cover 200 valid JSON, 401, 429, malformed API
JSON, missing choices, markdown-fenced plan output, and network timeout.

### WP-06 — Plan rendering and storage

**Files:** `src/ashlib/render.py`, `src/ashlib/plan.py`, `tests/test_render.py`

**Task:** Produce stable human-readable plan output and persist/load the current
validated plan. Replace existing plans only after an explicit callback confirms.

**Acceptance:** rendered output includes step number, command, why, risk,
expected result, and exact `ash run`/`ash discard` next actions.

### WP-07 — Safe executor and run logs

**Files:** `src/ashlib/executor.py`, `tests/test_executor.py`

**Task:** Execute one validated command at a time without `shell=True`. Require
literal `yes` using an injectable confirmation function according to section
4.3. Stream combined output to a timestamped log, stop at first nonzero exit,
and redact output before displaying/writing it.

**Acceptance:** mocked subprocess tests prove no command runs when confirmation
is declined; `--yes` refuses prohibited-risk plans; execution stops after the
first failure; and logs contain no configured secret.

### WP-08 — Doctor and compatibility profile

**Files:** `src/ashlib/doctor.py`, `tests/test_doctor.py`

**Task:** Check required executables, data-directory writeability, launcher
PATH presence, config parseability, and report a static compatibility profile
used by the provider prompt.

**Acceptance:** doctor exits zero in a valid temporary home; missing Python,
unwritable directory, malformed config, and missing PATH block each produce an
actionable nonzero result.

### WP-09 — Integration wiring and documentation

**Files:** `src/ashlib/cli.py`, `README.md`, `tests/test_integration.py`

**Task:** Connect completed modules to all section-5 commands. Document the
install sequence, BYOK scope, a-Shell limitations, confirmation behavior,
uninstall, and troubleshooting.

**Acceptance:** an integration test using a fake provider completes:
setup → plan → plan display → confirmed run → run log → discard.

## 11. Global verification gate

Before tagging v0.1.0, one integrator must run:

```sh
python3 -m unittest discover -s tests -v
sh -n install.sh
sh -n uninstall.sh
python3 src/ash.py --help
python3 src/ash.py version
```

Manual a-Shell Beta smoke test:

1. Extract a release archive and install from its local directory.
2. Restart a-Shell and verify `ash version` resolves without a manual PATH edit.
3. Configure a disposable API key.
4. Request `install jq`; verify no command executes before `ash run`.
5. Decline confirmation; verify nothing executes.
6. Approve confirmation; verify the exact displayed command executes and is
   logged without the API key.
7. Run `ash key clear`; confirm status reports no key.

## 12. Release criteria

v0.1.0 is ready only when all tests pass, the manual smoke test passes on the
current a-Shell Beta, no third-party Python dependency exists, and a reviewer
confirms the command validator rejects every section-8 prohibited construct.

## 13. Deferred work

- Additional providers and OAuth flows.
- Native iOS Keychain companion.
- Shortcuts/App Intents integration.
- User-approved diagnostic context collection.
- Signed release manifest, update checker, and rollback support.
- A reviewed, versioned a-Shell capability database.
