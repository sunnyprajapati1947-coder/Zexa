#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
export PREFIX
export SVDIR="$PREFIX/var/service"
export LOGDIR="$PREFIX/var/log"

if ! command -v sv >/dev/null 2>&1 || ! command -v service-daemon >/dev/null 2>&1; then
  echo "Termux:Services is required. Run: pkg install termux-services; then reopen Termux."
  exit 1
fi
SERVICE_DIR="$SVDIR/zexa-worker"
if [ ! -x "$SERVICE_DIR/run" ]; then
  echo "Zexa worker service is not installed. Run scripts/install-termux-worker.sh first."
  exit 1
fi

BOOT_DIR="$HOME/.termux/boot"
mkdir -p "$BOOT_DIR"
chmod 700 "$BOOT_DIR"
cat > "$BOOT_DIR/00-start-zexa-worker" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
export PREFIX=/data/data/com.termux/files/usr
export SVDIR="$PREFIX/var/service"
export LOGDIR="$PREFIX/var/log"
export PATH="$PREFIX/bin:$PATH"

if ! pgrep -f "runsvdir $SVDIR" >/dev/null 2>&1; then
  service-daemon start
  sleep 2
fi
sv up zexa-worker
EOF
chmod 700 "$BOOT_DIR/00-start-zexa-worker"

echo "Optional Termux:Boot startup hook installed."
echo "Install/open the Termux:Boot Android add-on once, then reboot to verify."
echo "No wake lock is acquired automatically; enable one only if you accept the battery cost."
