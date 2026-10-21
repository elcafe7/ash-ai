#!/bin/sh
# Remove only this application's fixed Documents data root and marked PATH block.
set -eu

APP_ROOT=$HOME/Documents/.ash-ai
BIN_DIR=$HOME/Documents/bin
PROFILE=$HOME/.profile
SENTINEL=$APP_ROOT/install.json
MARKER="# ash-ai PATH BEGIN"
END_MARKER="# ash-ai PATH END"

if [ ! -f "$SENTINEL" ]; then
  echo "Refusing to uninstall: ash install sentinel is missing at $SENTINEL." >&2
  exit 2
fi

rm -rf "$APP_ROOT"
if [ -f "$BIN_DIR/ash" ] && grep -Fq 'Documents/.ash-ai/app/ash.py' "$BIN_DIR/ash"; then
  rm -f "$BIN_DIR/ash"
fi

if [ -f "$PROFILE" ] && grep -Fq "$MARKER" "$PROFILE"; then
  TMP_PROFILE=$PROFILE.ash-tmp.$$
  awk -v start="$MARKER" -v finish="$END_MARKER" '
    $0 == start { skip=1; next }
    skip && $0 == finish { skip=0; next }
    !skip { print }
  ' "$PROFILE" > "$TMP_PROFILE"
  mv "$TMP_PROFILE" "$PROFILE"
fi

echo "ash-ai data and its marked launcher/PATH entry were removed."
