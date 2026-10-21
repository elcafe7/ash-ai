#!/bin/sh
# Install from an extracted ash-ai release directory.
set -eu

# POSIX path handling: resolve this script's directory without relying on Bash.
SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" 2>/dev/null && pwd -P) || {
  echo "Cannot resolve release directory." >&2
  exit 2
}
SOURCE_DIR=$SCRIPT_DIR
DOCUMENTS_DIR=$HOME/Documents
APP_ROOT=$DOCUMENTS_DIR/.ash-ai
APP_DIR=$APP_ROOT/app
BIN_DIR=$DOCUMENTS_DIR/bin
LAUNCHER=$BIN_DIR/ash
PROFILE=$HOME/.profile
STAGE=$APP_ROOT/.app-stage.$$

if [ ! -f "$SOURCE_DIR/src/ash.py" ] || [ ! -d "$SOURCE_DIR/src/ashlib" ]; then
  echo "install.sh must be run from a complete extracted ash-ai release directory." >&2
  exit 2
fi

# a-Shell owns its sandbox and exposes Documents as the user-writable root.
# Do not create HOME, Documents, or parent sandbox directories: some builds
# reject it and a wrong HOME would put the installation outside a-Shell.
if [ ! -d "$DOCUMENTS_DIR" ] || [ ! -w "$DOCUMENTS_DIR" ]; then
  echo "a-Shell Documents directory is unavailable or not writable: $DOCUMENTS_DIR" >&2
  echo "Open a-Shell once, then run this installer from its Documents area." >&2
  exit 2
fi
mkdir "$APP_ROOT" 2>/dev/null || [ -d "$APP_ROOT" ] || {
  echo "Cannot create ash-ai data directory: $APP_ROOT" >&2
  exit 2
}
mkdir "$BIN_DIR" 2>/dev/null || [ -d "$BIN_DIR" ] || {
  echo "Cannot create a-Shell user bin directory: $BIN_DIR" >&2
  exit 2
}
chmod 700 "$APP_ROOT" 2>/dev/null || true

if [ -e "$LAUNCHER" ] && ! grep -Fq 'Documents/.ash-ai/app/ash.py' "$LAUNCHER"; then
  echo "Refusing to overwrite non-ash launcher: $LAUNCHER" >&2
  exit 2
fi

# Prepare and verify the replacement before touching the installed app.
rm -rf "$STAGE"
mkdir "$STAGE"
cp -R "$SOURCE_DIR/src" "$STAGE/app"
if [ ! -f "$STAGE/app/ash.py" ] || [ ! -d "$STAGE/app/ashlib" ]; then
  rm -rf "$STAGE"
  echo "Staged release failed verification; existing installation is unchanged." >&2
  exit 2
fi

BACKUP=
if [ -e "$APP_DIR" ]; then
  n=1
  while [ "$n" -le 5 ]; do
    CANDIDATE=$APP_ROOT/app.backup.$(date +%Y%m%dT%H%M%S).$n
    if [ ! -e "$CANDIDATE" ]; then BACKUP=$CANDIDATE; break; fi
    n=$((n + 1))
  done
  if [ -z "$BACKUP" ]; then
    rm -rf "$STAGE"
    echo "Too many retained app backups; remove an old backup before installing." >&2
    exit 2
  fi
  # Keep at most five backups; only these fixed app.backup.* paths are eligible.
  count=0
  for old in "$APP_ROOT"/app.backup.*; do
    [ -e "$old" ] || continue
    count=$((count + 1))
  done
  if [ "$count" -ge 5 ]; then
    oldest=
    for old in "$APP_ROOT"/app.backup.*; do
      [ -e "$old" ] || continue
      if [ -z "$oldest" ] || [ "$old" -ot "$oldest" ]; then oldest=$old; fi
    done
    [ -n "$oldest" ] && rm -rf "$oldest"
  fi
  mv "$APP_DIR" "$BACKUP"
fi

if ! mv "$STAGE/app" "$APP_DIR"; then
  [ -n "$BACKUP" ] && [ -e "$BACKUP" ] && mv "$BACKUP" "$APP_DIR"
  rm -rf "$STAGE"
  echo "Could not replace app; previous installation restored where possible." >&2
  exit 2
fi
rmdir "$STAGE"

# The sentinel is created only after the staged application is installed.
SENTINEL_TMP=$APP_ROOT/.install.json.$$
cat > "$SENTINEL_TMP" <<'EOF'
{"application":"ash-ai","install_format":1}
EOF
chmod 600 "$SENTINEL_TMP" 2>/dev/null || true
mv "$SENTINEL_TMP" "$APP_ROOT/install.json"

TMP_LAUNCHER=$BIN_DIR/.ash.new.$$
cat > "$TMP_LAUNCHER" <<'EOF'
#!/bin/sh
exec python3 "$HOME/Documents/.ash-ai/app/ash.py" "$@"
EOF
chmod 700 "$TMP_LAUNCHER"
if ! mv "$TMP_LAUNCHER" "$LAUNCHER"; then
  rm -f "$TMP_LAUNCHER"
  echo "App installed, but launcher replacement failed." >&2
  exit 2
fi

PROFILE_MARKER="# ash-ai PATH BEGIN"
PROFILE_END="# ash-ai PATH END"
if [ ! -f "$PROFILE" ] || ! grep -Fq "$PROFILE_MARKER" "$PROFILE"; then
  {
    echo "$PROFILE_MARKER"
    echo 'export PATH="$HOME/Documents/bin:$PATH"'
    echo "$PROFILE_END"
  } >> "$PROFILE"
fi

[ -z "$BACKUP" ] || echo "Previous app saved at $BACKUP"
echo "Installed ash. Restart a-Shell, then run: ash setup"
