#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
export PREFIX
export SVDIR="$PREFIX/var/service"
export LOGDIR="$PREFIX/var/log"

VENV_ZEXA="$ROOT/.venv/bin/zexa"
if [ -x "$VENV_ZEXA" ]; then
  ZEXA_BIN="$VENV_ZEXA"
elif command -v zexa >/dev/null 2>&1; then
  ZEXA_BIN="$(command -v zexa)"
else
  echo "Zexa CLI is not installed. Run: python -m pip install -e ."
  exit 1
fi

if ! command -v sv-enable >/dev/null 2>&1 || ! command -v sv >/dev/null 2>&1; then
  echo "Termux:Services is missing. Run: pkg install termux-services; then reopen Termux."
  exit 1
fi
if ! command -v service-daemon >/dev/null 2>&1; then
  echo "Termux:Services daemon is unavailable. Reopen Termux after installing termux-services."
  exit 1
fi

SERVICE_DIR="$SVDIR/zexa-worker"
mkdir -p "$SERVICE_DIR" "$HOME/.zexa"
chmod 700 "$HOME/.zexa"

cat > "$SERVICE_DIR/run" <<EOF
#!/data/data/com.termux/files/usr/bin/sh
umask 077
export PATH="$ROOT/.venv/bin:$PREFIX/bin"
export ZEXA_ENV_FILE="$ROOT/.env"
export ZEXA_JOB_DB="$HOME/.zexa/jobs.sqlite3"
export ZEXA_AUDIT_DB="$HOME/.zexa/audit.sqlite3"
cd "$ROOT" || exit 1
exec "$ZEXA_BIN" worker --poll-seconds 5
EOF
chmod 700 "$SERVICE_DIR/run"

if ! pgrep -f "runsvdir $SVDIR" >/dev/null 2>&1; then
  service-daemon start
  sleep 2
fi
sv-enable zexa-worker

echo "Zexa worker service enabled and started."
echo "Queue database: $HOME/.zexa/jobs.sqlite3"
echo "Environment file: $ROOT/.env"
echo "Check: sv status zexa-worker"
echo "Stop:  sv down zexa-worker"
echo "Disable startup: sv-disable zexa-worker"
