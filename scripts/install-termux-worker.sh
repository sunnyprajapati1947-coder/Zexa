#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

if ! command -v zexa >/dev/null 2>&1; then
  echo "Zexa CLI is not installed. From the repository run: python -m pip install -e ."
  exit 1
fi
if ! command -v sv-enable >/dev/null 2>&1 || ! command -v sv >/dev/null 2>&1; then
  echo "Termux:Services is missing. Run: pkg install termux-services; then reopen Termux."
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_DIR="${PREFIX:?Run this inside Termux}/var/service/zexa-worker"
mkdir -p "$SERVICE_DIR" "$HOME/.zexa"
chmod 700 "$HOME/.zexa"

# Generate the runit entrypoint with this checkout's absolute path. The worker
# and CLI therefore share one stable queue database regardless of runit cwd.
cat > "$SERVICE_DIR/run" <<EOF
#!/data/data/com.termux/files/usr/bin/sh
umask 077
export ZEXA_ENV_FILE="$ROOT/.env"
export ZEXA_JOB_DB="$HOME/.zexa/jobs.sqlite3"
export ZEXA_AUDIT_DB="$HOME/.zexa/audit.sqlite3"
cd "$ROOT"
exec zexa worker --poll-seconds 5
EOF
chmod 700 "$SERVICE_DIR/run"

sv-enable zexa-worker
sv up zexa-worker

echo "Zexa worker service enabled and started."
echo "Queue database: $HOME/.zexa/jobs.sqlite3"
echo "Environment file: $ROOT/.env"
echo "Check: sv status zexa-worker"
echo "Stop:  sv down zexa-worker"
echo "Disable startup: sv-disable zexa-worker"
