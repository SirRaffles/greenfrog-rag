#!/bin/bash
#
# Entrypoint script for the scraper container
# Handles both cron mode (default) and manual execution
#

set -e

LOG_DIR="${LOG_DIR:-/logs}"
DATA_DIR="${DATA_DIR:-/data}"

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log "=================================="
log "GreenFrog Scraper Container"
log "=================================="
log "Mode: $1"
log "LOG_DIR: ${LOG_DIR}"
log "DATA_DIR: ${DATA_DIR}"
log ""

# Ensure required directories exist
mkdir -p "${LOG_DIR}" "${DATA_DIR}" "${DATA_DIR}/state"

# Set permissions
chmod 755 /app/run_scraper.sh 2>/dev/null || true
chmod 755 /app/scrape_matcha.py 2>/dev/null || true
chmod 755 /app/sync_to_anythingllm.py 2>/dev/null || true

# Handle different execution modes
case "$1" in
    cron|-f)
        log "Starting in CRON mode (scheduled daily runs)"
        log "Cron schedule: Daily at 2 AM (0 2 * * *)"
        log ""

        # Run initial scrape on startup (optional)
        if [ "${RUN_ON_STARTUP}" = "true" ]; then
            log "RUN_ON_STARTUP=true, executing initial scrape..."
            /app/run_scraper.sh || log "Initial scrape failed (non-fatal)"
            log ""
        fi

        # Start cron in foreground
        log "Starting cron daemon..."
        exec cron -f
        ;;

    manual|run|now)
        log "Running manual scrape NOW..."
        log ""
        exec /app/run_scraper.sh
        ;;

    scrape-only)
        log "Running scraper ONLY (no sync)..."
        log ""
        exec python3 /app/scrape_matcha.py
        ;;

    sync-only)
        log "Running sync ONLY (no scrape)..."
        log ""
        exec python3 /app/sync_to_anythingllm.py
        ;;

    bash|sh)
        log "Starting interactive shell..."
        log ""
        exec /bin/bash
        ;;

    *)
        if [ -z "$1" ]; then
            log "No command specified, starting in CRON mode"
            exec "$0" cron
        else
            log "Unknown mode: $1"
            log ""
            log "Available modes:"
            log "  cron|-f        - Run cron daemon (default, scheduled at 2 AM daily)"
            log "  manual|run|now - Execute scraper immediately"
            log "  scrape-only    - Run scraper without sync"
            log "  sync-only      - Run sync without scraper"
            log "  bash|sh        - Interactive shell"
            log ""
            exit 1
        fi
        ;;
esac
