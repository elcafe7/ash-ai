# ash-ai

`ash` is a dependency-free, BYOK AI helper for a-Shell Beta. On first launch,
its terminal menu asks you to select **OpenRouter**, **xAI**, or **OpenAI**,
then prompts for a model and API key. It remembers that provider preference
locally. It asks the selected OpenAI-compatible API for a constrained JSON command plan, validates it
locally, shows it to you, and only executes it after your explicit approval.

It is not a general Linux installer. a-Shell supports its own `pkg` command
for compatible WASM tools and pure-Python packages only; native Python wheels
are outside ash-ai's scope.

## Install

Download and extract a release archive, then run the installer from the
extracted release directory:

```sh
cd /path/to/extracted/ash-ai-release
sh ./install.sh
```

Restart a-Shell so it reads the marked PATH entry in `~/.profile`, then:

```sh
ash setup
ash "install jq"
ash run
```

The installer makes no network request and does not invoke `pip` or `pkg`.
It installs files under `~/Documents/.ash-ai/` and the launcher at
`~/Documents/bin/ash`. It verifies that a-Shell's existing `~/Documents`
directory is writable; it never tries to create `HOME`, `Documents`, or a
parent sandbox directory.

## Safety

- The API key is stored as plaintext in the a-Shell Documents container at
  `~/Documents/.ash-ai/config.json`. It is not stored in iOS Keychain. It is
  never printed, included in command plans, or written to run logs.
- A model response cannot run immediately. It must pass the local schema and
  command validator, be saved as the current plan, and then be confirmed.
- Every executable step requires the literal `yes` confirmation.
- v0.1 rejects redirections, pipelines, substitutions, shell operators, and
  Linux package managers rather than attempting to interpret them.

Useful commands: `ash status`, `ash plan`, `ash discard`, `ash doctor`, and
`ash key clear`. To uninstall, run `sh ./uninstall.sh` from the extracted
release directory. Uninstall verifies the ash install sentinel before
removing the fixed `~/Documents/.ash-ai` application data root.

`ash debug` is an offline debugger: it neither contacts an AI provider nor
executes commands. It checks the saved setup and examines the latest redacted
run log for known issues such as missing commands, unsupported Python modules,
permissions, network failures, or API authentication/rate-limit errors.

Run `ash` with no arguments to reopen the navigation menu and change the
saved provider at any time. `ash setup` does the same directly. The built-in
provider endpoints are OpenRouter (`https://openrouter.ai/api/v1`), xAI
(`https://api.x.ai/v1`), and OpenAI (`https://api.openai.com/v1`); users enter
their own model identifier and key.

On a-Shell, the setup key prompt is intentionally visible: Python's hidden
`getpass` prompt can freeze its terminal bridge. Do not share screenshots or
terminal history containing that entry; the installer stores the key locally
in its plaintext configuration file.

## Development checks

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
sh -n install.sh
sh -n uninstall.sh
PYTHONPATH=src python3 src/ash.py version
```
