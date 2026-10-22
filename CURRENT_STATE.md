# ash-ai: Current State

**Repository:** https://github.com/elcafe7/ash-ai  
**Branch:** `main`  
**Current baseline:** `da2156d` — 44 automated tests passing

## What the app is

`ash-ai` is a dependency-free Python helper for **a-Shell on iOS**. It lets a
user select OpenRouter, xAI, or OpenAI; stores the selected provider/model/API
key locally; requests a constrained command plan; displays that plan; and runs
each step only after the user types literal `yes`.

It is deliberately **not** a general Linux package manager or arbitrary-shell
agent. a-Shell is not Linux and its supported commands/packages are limited.

## iPhone/a-Shell instructions

The clone created by `lg2` is named `ash-ai.git`.

### Update to the current version

```sh
cd ~/Documents/ash-ai.git
lg2 pull
sh install.sh
```

### Start ash-ai

Use the direct launcher; this avoids relying on PATH/profile reload behavior:

```sh
python3 ~/Documents/.ash-ai/app/ash.py
```

For provider setup:

```sh
python3 ~/Documents/.ash-ai/app/ash.py setup
```

Choose OpenRouter, xAI, or OpenAI, then supply a model ID and API key. a-Shell
cannot reliably use Python's hidden-password prompt, so the API key entry is
visible while typed/pasted. Do not share terminal screenshots or history with
the key present.

For OpenAI, `gpt-5.6-terra` is the current recommended balance of capability
and cost. The helper uses Chat Completions and does not require a reasoning
level; provider defaults apply.

### Safe test

`jq` is **not** a verified a-Shell `pkg` package. The app now rejects it rather
than creating a false plan. Test with a verified a-Shell package instead:

```sh
python3 ~/Documents/.ash-ai/app/ash.py install zip
python3 ~/Documents/.ash-ai/app/ash.py run
```

Review the displayed command and type `yes` only if it is correct. The current
verified a-Shell `pkg` catalog is: `ffmpeg`, `unzip`, `xz`, and `zip`.

## Security and behavior

- A model response is treated as untrusted input.
- Only a strict allowlist of single-process commands can run.
- Every executable step requires literal `yes`; there is no `--yes` bypass.
- Provider endpoints are pinned by provider ID; config cannot redirect a
  bearer token to another URL.
- Config, plans, and run logs use private file modes where a-Shell supports
  them.
- The API key is plaintext in a-Shell Documents storage, not iOS Keychain.
- The installer requires an existing writable `~/Documents` and creates only
  ash-ai's own children; it does not create sandbox parent directories.
- The uninstaller requires an ash-ai sentinel before deleting its fixed data
  root.

## Known boundary / next validation

The full automated suite passes, but the final product gate remains an actual
a-Shell Beta device check that its Python `subprocess.run` bridge can invoke
the permitted a-Shell commands such as `pkg install zip`. If a-Shell does not
support that bridge, the executor needs an a-Shell-specific adapter.
