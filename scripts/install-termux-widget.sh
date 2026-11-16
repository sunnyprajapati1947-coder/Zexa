#!/data/data/com.termux/files/usr/bin/bash
# Install optional Termux:Widget shortcuts for Zexa and selected app links.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SHORTCUT_DIR="$HOME/.shortcuts"
ZEXA_BIN="$ROOT/.venv/bin/zexa"

if [ ! -x "$ZEXA_BIN" ]; then
  echo "Zexa CLI not found at $ZEXA_BIN"
  echo "Run: python -m pip install -e ."
  exit 1
fi

mkdir -p "$SHORTCUT_DIR"
chmod 700 "$SHORTCUT_DIR"

backup_target() {
  local target="$1" backup
  if [ -e "$target" ]; then
    backup="$target.zexa-backup.$(date +%s).$$.bak"
    cp -p "$target" "$backup"
    echo "Backed up existing shortcut: $backup"
  fi
}

write_zexa_shortcut() {
  local name="$1"
  shift
  local target="$SHORTCUT_DIR/$name"
  backup_target "$target"
  {
    printf '%s\n' '#!/data/data/com.termux/files/usr/bin/sh'
    printf 'ROOT=%q\n' "$ROOT"
    printf 'ZEXA_BIN=%q\n' "$ZEXA_BIN"
    printf '%s\n' 'cd "$ROOT" || exit 1'
    printf '%s' 'exec "$ZEXA_BIN"'
    printf ' %q' "$@"
    printf '\n'
  } > "$target"
  chmod 700 "$target"
  echo "Installed: $target"
}

write_url_shortcut() {
  local name="$1" url="$2"
  local target="$SHORTCUT_DIR/$name"
  backup_target "$target"
  {
    printf '%s\n' '#!/data/data/com.termux/files/usr/bin/sh'
    printf 'URL=%q\n' "$url"
    cat <<'EOF'
if command -v termux-open-url >/dev/null 2>&1; then
  exec termux-open-url "$URL"
fi
exec am start -a android.intent.action.VIEW -d "$URL"
EOF
  } > "$target"
  chmod 700 "$target"
  echo "Installed: $target"
}

write_zexa_shortcut "zexa-voice" voice
write_zexa_shortcut "zexa-converse" converse
write_zexa_shortcut "zexa-jobs" jobs --limit 20
write_zexa_shortcut "zexa-capabilities" android

# Android's normal link resolver may open the matching installed app or
# present a browser/app chooser. These shortcuts do not sign in, post,
# message, or change anything inside the target apps.
write_url_shortcut "open-x" "https://x.com/"
write_url_shortcut "open-linkedin" "https://www.linkedin.com/"
write_url_shortcut "open-kimi" "https://www.kimi.com/"
write_url_shortcut "open-maps" "https://www.google.com/maps/"

echo
echo "Zexa shortcuts installed in $SHORTCUT_DIR."
echo "Install/open the Termux:Widget Android add-on, then refresh its widget."
echo "Voice shortcuts start only after you tap them; no background microphone is enabled."
