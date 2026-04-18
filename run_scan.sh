#!/bin/bash
# run_scan.sh — Fortress Scanner Cron Runner (Task B6)
#
# Usage:
#   ./run_scan.sh NSE   # Scan NSE (India) — run at 11:00 UTC Mon-Fri
#   ./run_scan.sh US    # Scan US  (S&P 500) — run at 23:00 UTC Mon-Fri
#
# Cron setup (as 'fortress' user):
#   # /etc/cron.d/fortress-scanner
#   0 11 * * 1-5 fortress /opt/fortress-scanner/run_scan.sh NSE >> /var/log/fortress/nse_scan.log 2>&1
#   0 23 * * 1-5 fortress /opt/fortress-scanner/run_scan.sh US  >> /var/log/fortress/us_scan.log  2>&1

set -euo pipefail

MARKET="${1:-NSE}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================"
echo "Fortress Scanner — Market: $MARKET"
echo "Started: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "======================================"

# ── Activate virtualenv if it exists ─────────────────────────────────────────
VENV_PATH="$SCRIPT_DIR/.venv"
if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
    echo "Activated virtualenv: $VENV_PATH"
else
    echo "Warning: No .venv found at $VENV_PATH — using system Python."
fi

# ── Load .env ─────────────────────────────────────────────────────────────────
ENV_FILE="$SCRIPT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    # Export all vars from .env (strips comments and blanks)
    set -a
    source "$ENV_FILE"
    set +a
    echo "Loaded environment from $ENV_FILE"
else
    echo "Warning: No .env file found at $ENV_FILE"
fi

# ── Validate required environment ────────────────────────────────────────────
if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL is not set. Cannot proceed."
    exit 1
fi

# ── Run the scanner ───────────────────────────────────────────────────────────
cd "$SCRIPT_DIR"
python scanner_db_writer.py --market "$MARKET"
EXIT_CODE=$?

echo "======================================"
echo "Finished: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "Exit code: $EXIT_CODE"
echo "======================================"

exit $EXIT_CODE
