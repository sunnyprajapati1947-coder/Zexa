#!/data/data/com.termux/files/usr/bin/bash
# Install optional Termux:Widget shortcuts for Zexa.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
SHORTCUT_DIR="$HOME/.shortcuts"
ZEXA_BIN="$ROOT/.venv/bin/zexa"

if [ ! -x "$ZEXA_BIN" ]; then
  echo "Zexa CLI not found at $ZEXA_BIN"
  echo "Run: python -m pip install -e ."
  exit 1
fi
if ! command -v termux-toast >/dev/null 2>&1; then
  echo "Termux:API commands are optional; install termux-api for toast feedback."
fi

mkdir -p "$SHORTCUT_DIR"
chmod 700 "$SHORTCUT_DIR"

install_shortcut() {
  local name="$1"
  local body="$2"
  local target="$SHORTCUT_DIR/$name"
  if [ -e "$target" ]; then
    cp -p "$target" "$target.zexa-backup"
    echo "Backed up existing shortcut: $target.zexa-backup"
  fi
  printf '%s\n' "$body" > "$target"
  chmod 700 "$target"
  echo "Installed: $target"
}

install_shortcut "zexa-voice" "#!/data/data/com.termux/files/usr/bin/sh
ROOT='$ROOT'
cd \"\$ROOT\" || exit 1
exec \"\$ROOT/.venv/bin/zexa\" voice"

install_shortcut "zexa-converse" "#!/data/data/com.termux/files/usr/bin/sh
ROOT='$ROOT'
cd \"\$ROOT\" || exit 1
exec \"\$ROOT/.venv/bin/zexa\" converse"

install_shortcut "zexa-jobs" "#!/data/data/com.termux/files/usr/bin/sh
ROOT='$ROOT'
cd \"\$ROOT\" || exit 1
exec \"\$ROOT/.venv/bin/zexa\" jobs --limit 20"

install_shortcut "zexa-capabilities" "#!/data/data/com.termux/files/usr/bin/sh
ROOT='$ROOT'
cd \"\$ROOT\" || exit 1
exec \"\$ROOT/.venv/bin/zexa\" android"

echo
echo "Zexa shortcuts installed in $SHORTCUT_DIR."
echo "Install/open the Termux:Widget Android add-on, then refresh its widget."
echo "Voice shortcuts start only after you tap them; no background microphone is enabled."
