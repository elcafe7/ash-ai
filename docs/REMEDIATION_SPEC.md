# Security and Release Remediation Specification

## Release position

v0.1.0 is **blocked** until every P0/P1 item below passes automated tests.
No packet may relax the existing “user sees the command before it runs” rule.

## Non-negotiable rules

1. A model response is untrusted input.
2. Every executable model-generated step requires literal `yes`; `--yes` is
   removed in this release rather than made clever.
3. The validator accepts only a positive allowlist of safe, single-process
   a-Shell operations. It rejects shell/interpreter launchers and arbitrary
   program execution.
4. Provider endpoints are derived from a provider ID; a file may never choose
   the bearer-token destination.
5. Every persisted ash file is explicitly mode `0600`; data directories are
   mode `0700` where the platform supports modes.
6. API keys are plaintext in the a-Shell Documents container, not Keychain.
   Documentation must say so accurately.
7. Release shell scripts must never recursively delete an environment-selected
   path.

## Positive execution allowlist (v0.1.1)

Only these exact argv patterns may become executable plan steps:

| Program | Permitted arguments |
|---|---|
| `pkg` | `install <package-name>` where package name matches `[A-Za-z0-9][A-Za-z0-9._-]{0,63}` |
| `pip` / `pip3` | `install <package-name>` with same package pattern; model must label it `network` |
| `python3` | `-m pip install <package-name>` with same pattern; model must label it `network` |
| `help` | `-l` only |
| `which` | one safe command name |
| `command` | `-v <safe-command-name>` only |
| `pwd` | no arguments |
| `ls` | no arguments or one relative path without `..` |
| `pkg` / `pip` / `pip3` / `python3` verification | `--version` only |

No `rm`, `curl`, `sh`, `bash`, `zsh`, `python -c`, `env`, `find`, redirection,
pipe, command substitution, absolute paths, or `..` are permitted. Unknown
commands are a validation error and must be shown as `unsupported`, not run.

## Work packets

Each packet is written for a low-reasoning coding agent. Change only listed
files, add tests, and run the named test module. Do not redesign the policy.

### R-01: Local execution policy and consent

**Files:** `src/ashlib/safety.py`, `src/ashlib/plan.py`,
`src/ashlib/executor.py`, `tests/test_safety.py`, `tests/test_plan.py`,
`tests/test_executor.py`

**Implement:** exact allowlist above; reject control characters in every
displayed schema field; all steps require literal `yes`; remove CLI `--yes`.
Model risk is display metadata only, never an authorization signal.

**Acceptance:** tests prove `rm`, `sh -c`, `python3 -c`, `curl`, `find -exec`,
and a command falsely marked `read_only` cannot execute; all valid allowlist
forms require confirmation; ESC/OSC values in summary/reason/why/expected fail.

### R-02: Pinned providers and safe local persistence

**Files:** `src/ashlib/config.py`, `src/ashlib/provider.py`,
`src/ashlib/plan.py`, `src/ashlib/executor.py`, `src/ashlib/debugger.py`,
`tests/test_config.py`, `tests/test_provider.py`, `tests/test_executor.py`

**Implement:** remove persisted `base_url`; derive URL from `PROVIDERS` on load
and request. Create plans/logs atomically at `0600`, runs directory at `0700`,
using collision-safe log names. Redact configured keys in rendered command text
and reject command strings containing credential-shaped assignments/headers.

**Acceptance:** a tampered legacy/malformed URL cannot direct a request; plan
and log modes are `0600` under umask `022`; rapid logs never collide; key text
is absent from rendered/logged command text.

### R-03: Safe installer/uninstaller and accurate docs

**Files:** `install.sh`, `uninstall.sh`, `README.md`, `SPEC.md`,
`tests/test_install_scripts.py`

**Implement:** eliminate `ASH_AI_HOME`/`ASH_SOURCE_DIR` overrides from release
scripts; use POSIX-compatible path handling; refuse installer unless a local
release tree is present; never overwrite a non-ash launcher; stage/copy/verify
before replacing `app`; use bounded app backups. Uninstaller must require an
ash sentinel and delete only its fixed `$HOME/Documents/.ash-ai` root; remove
only a bounded PATH marker block. State extracted-release installation only;
do not advertise curl-pipe-sh. Clearly document plaintext Documents key storage.

**Acceptance:** shell syntax passes; static tests prove uninstall refuses a
missing sentinel and no override references remain; docs contain no one-line
install claim or Keychain-equivalent claim.

### R-04: CLI/doctor resilience

**Files:** `src/ashlib/cli.py`, `src/ashlib/doctor.py`,
`tests/test_cli.py`, `tests/test_doctor.py`

**Implement:** remove `run --yes`; reject unknown flags as usage errors rather
than AI tasks; gracefully handle `EOFError` and `KeyboardInterrupt`; doctor
checks app/launcher, executable PATH, and its own marked profile block. Curl is
informational, not a failure, because the runtime uses urllib.

**Acceptance:** unknown dash flags return nonzero without API calls; EOF/Ctrl-C
does not traceback; missing curl is WARN; broken PATH/profile reports FAIL.

### R-05: Integrator verification

**Files:** any only to resolve integration defects; `README.md` test count if
needed.

**Implement:** run all tests and add cross-module regressions. Do not broaden
the allowlist or weaken confirmation to make a test pass.

**Acceptance:** full suite passes; `sh -n install.sh`; `sh -n uninstall.sh`;
manual test transcript documents that malicious commands do not run.

## Post-remediation manual gate

On an actual a-Shell Beta device, test installation from an extracted release,
menu setup, a denied `pkg install` plan, an approved `pkg install` plan, and
the actual a-Shell command execution bridge. If `subprocess.run` cannot invoke
a-Shell commands, v0.1.1 remains blocked until a supported execution adapter
is implemented.
