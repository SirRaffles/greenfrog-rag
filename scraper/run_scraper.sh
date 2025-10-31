#!/bin/bash
#
# Wrapper script for running the Matcha Initiative scraper
# Executes both scraping and syncing to AnythingLLM
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${LOG_DIR:-/logs}"
DATA_DIR="${DATA_DIR:-/data}"

# Timestamp for this run
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RUN_LOG="${LOG_DIR}/scraper-run-${TIMESTAMP}.log"

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${RUN_LOG}"
}

log "=================================="
log "GreenFrog Scraper - Starting Run"
log "=================================="
log "Timestamp: ${TIMESTAMP}"
log "Script directory: ${SCRIPT_DIR}"
log "Log directory: ${LOG_DIR}"
log "Data directory: ${DATA_DIR}"
log ""

# Ensure required directories exist
mkdir -p "${LOG_DIR}" "${DATA_DIR}" "${DATA_DIR}/state"

# Step 1: Scrape website content
log "STEP 1: Scraping The Matcha Initiative website..."
log "--------------------------------------------------"

if python3 "${SCRIPT_DIR}/scrape_matcha.py" 2>&1 | tee -a "${RUN_LOG}"; then
    log "✓ Scraping completed successfully"
else
    EXIT_CODE=$?
    log "✗ Scraping failed with exit code ${EXIT_CODE}"
    log "Check ${RUN_LOG} for details"
    exit ${EXIT_CODE}
fi

log ""

# Step 2: Sync content to AnythingLLM
log "STEP 2: Syncing content to AnythingLLM..."
log "--------------------------------------------------"

# Wait a moment to ensure AnythingLLM is ready
sleep 5

if python3 "${SCRIPT_DIR}/sync_to_anythingllm.py" 2>&1 | tee -a "${RUN_LOG}"; then
    log "✓ Sync completed successfully"
else
    EXIT_CODE=$?
    log "✗ Sync failed with exit code ${EXIT_CODE}"
    log "Check ${RUN_LOG} for details"
    exit ${EXIT_CODE}
fi

log ""

# Summary
log "=================================="
log "GreenFrog Scraper - Run Complete"
log "=================================="
log "Run log: ${RUN_LOG}"
log ""

# Cleanup old logs (keep last 30 days)
log "Cleaning up old logs..."
find "${LOG_DIR}" -name "scraper-run-*.log" -type f -mtime +30 -delete 2>/dev/null || true
log "✓ Log cleanup complete"
log ""

log "All operations completed successfully!"
exit 0
