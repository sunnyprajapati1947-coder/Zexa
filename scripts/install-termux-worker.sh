#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

if ! command -v zexa >/dev/null 2>&1; then
  echo "Zexa CLI is not installed. From the repository run: python -m pip install -e ."
  exit 1
fi
if ! command -v sv >/dev/null 2>&1; then
  echo "Termux:Services is missing. Install termux-services with pkg, then reopen Termux."
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_DIR="${PREFIX:?Run this inside Termux}/var/service/zexa-worker"
mkdir -p "$SERVICE_DIR"
cp "$ROOT/services/zexa-worker/run" "$SERVICE_DIR/run"
chmod 700 "$SERVICE_DIR/run"
sv up zexa-worker
echo "Zexa background worker service installed and started."
