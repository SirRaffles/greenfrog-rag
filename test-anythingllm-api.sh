#!/bin/bash

#############################################################################
# AnythingLLM Document Upload & Embed Test Script
#
# This script tests the complete document workflow:
# 1. Upload document to system storage
# 2. Embed document in workspace
# 3. Verify document appears in workspace
#
# Usage: ./test-anythingllm-api.sh [options]
#############################################################################

set -e

# Configuration
BASE_URL="${BASE_URL:-http://localhost:3001}"
API_KEY="${API_KEY:-sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA}"
WORKSPACE_SLUG="${WORKSPACE_SLUG:-greenfrog}"
TEST_FILE="${TEST_FILE:-/tmp/test-document.txt}"
VERBOSE="${VERBOSE:-0}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_debug() {
    if [ "$VERBOSE" -eq 1 ]; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

# Display usage
show_usage() {
    cat << EOF
Usage: $0 [options]

Options:
  --url URL              AnythingLLM base URL (default: http://localhost:3001)
  --key KEY              API key (default: from API_KEY env var)
  --workspace SLUG       Workspace slug (default: greenfrog)
  --file FILE            Test document path (default: /tmp/test-document.txt)
  --create-test-file     Create a test document before upload
  --verbose              Enable verbose output
  --upload-only          Only upload, skip embedding
  --embed-only           Only embed (document must exist)
  --verify               Verify document is embedded
  --help                 Show this help message

Environment Variables:
  BASE_URL               AnythingLLM URL
  API_KEY                API authentication key
  WORKSPACE_SLUG         Workspace identifier
  TEST_FILE              Path to document to upload
  VERBOSE                Enable debug output (0/1)

Examples:
  # Full workflow with test file creation
  ./test-anythingllm-api.sh --create-test-file

  # Custom workspace
  ./test-anythingllm-api.sh --workspace myworkspace --create-test-file

  # Upload only
  ./test-anythingllm-api.sh --upload-only --file /path/to/doc.pdf

  # Verbose output
  ./test-anythingllm-api.sh --create-test-file --verbose

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --url)
            BASE_URL="$2"
            shift 2
            ;;
        --key)
            API_KEY="$2"
            shift 2
            ;;
        --workspace)
            WORKSPACE_SLUG="$2"
            shift 2
            ;;
        --file)
            TEST_FILE="$2"
            shift 2
            ;;
        --create-test-file)
            CREATE_TEST_FILE=1
            shift
            ;;
        --upload-only)
            UPLOAD_ONLY=1
            shift
            ;;
        --embed-only)
            EMBED_ONLY=1
            shift
            ;;
        --verify)
            VERIFY_ONLY=1
            shift
            ;;
        --verbose)
            VERBOSE=1
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Create test document if requested
if [ "$CREATE_TEST_FILE" -eq 1 ]; then
    log_info "Creating test document: $TEST_FILE"
    cat > "$TEST_FILE" << 'EOF'
# Test Document

This is a test document for AnythingLLM API testing.

## Section 1: Overview
This document contains sample content to verify the upload and embedding workflow.

## Section 2: Details
The AnythingLLM API workflow consists of two main steps:
1. Upload the document to the system storage
2. Embed the document in the workspace

## Section 3: Verification
After embedding, the document should appear in the workspace and be available for RAG queries.

## Section 4: Testing
You can verify the document was successfully embedded by:
- Checking the AnythingLLM UI
- Querying the workspace with relevant questions
- Using the API to retrieve workspace documents

Created at: $(date)
EOF
    log_success "Test document created"
fi

# Validate prerequisites
if [ ! -f "$TEST_FILE" ] && [ "$EMBED_ONLY" -ne 1 ] && [ "$VERIFY_ONLY" -ne 1 ]; then
    log_error "Test file not found: $TEST_FILE"
    log_info "Use --create-test-file to create one, or specify --file PATH"
    exit 1
fi

# Extract filename and document path
FILENAME=$(basename "$TEST_FILE")
FILENAME_WITHOUT_EXT="${FILENAME%.*}"
DOC_LOCATION="custom-documents/${FILENAME_WITHOUT_EXT}.txt"

log_info "Configuration:"
log_info "  Base URL: $BASE_URL"
log_info "  Workspace: $WORKSPACE_SLUG"
log_info "  Document Location: $DOC_LOCATION"

echo ""

# ============================================================================
# STEP 1: Upload Document
# ============================================================================

if [ "$EMBED_ONLY" -ne 1 ] && [ "$VERIFY_ONLY" -ne 1 ]; then
    log_info "STEP 1: Uploading document to AnythingLLM..."

    UPLOAD_RESPONSE=$(curl -s -X POST \
        "${BASE_URL}/api/v1/document/upload" \
        -H "Authorization: Bearer ${API_KEY}" \
        -H "Content-Type: multipart/form-data" \
        -F "file=@${TEST_FILE}" \
        -w "\n%{http_code}")

    HTTP_CODE=$(echo "$UPLOAD_RESPONSE" | tail -n 1)
    BODY=$(echo "$UPLOAD_RESPONSE" | head -n -1)

    log_debug "HTTP Status: $HTTP_CODE"
    log_debug "Response: $BODY"

    if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 201 ]; then
        log_success "Document uploaded successfully"

        # Try to extract document location from response
        RETURNED_LOCATION=$(echo "$BODY" | grep -o '"location":"[^"]*"' | cut -d'"' -f4 || true)
        if [ -n "$RETURNED_LOCATION" ]; then
            DOC_LOCATION="$RETURNED_LOCATION"
            log_info "Document location: $DOC_LOCATION"
        fi
    else
        log_error "Upload failed with HTTP $HTTP_CODE"
        log_error "Response: $BODY"
        exit 1
    fi

    echo ""

    # Brief delay to allow file processing
    log_info "Waiting for document processing..."
    sleep 2
fi

# ============================================================================
# STEP 2: Embed Document in Workspace
# ============================================================================

if [ "$UPLOAD_ONLY" -ne 1 ] && [ "$VERIFY_ONLY" -ne 1 ]; then
    log_info "STEP 2: Embedding document in workspace '$WORKSPACE_SLUG'..."

    EMBED_PAYLOAD=$(cat <<EOF
{
  "adds": ["${DOC_LOCATION}"]
}
EOF
)

    log_debug "Embed payload: $EMBED_PAYLOAD"

    EMBED_RESPONSE=$(curl -s -X POST \
        "${BASE_URL}/api/v1/workspace/${WORKSPACE_SLUG}/update-embeddings" \
        -H "Authorization: Bearer ${API_KEY}" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -d "$EMBED_PAYLOAD" \
        -w "\n%{http_code}")

    HTTP_CODE=$(echo "$EMBED_RESPONSE" | tail -n 1)
    BODY=$(echo "$EMBED_RESPONSE" | head -n -1)

    log_debug "HTTP Status: $HTTP_CODE"
    log_debug "Response: $BODY"

    if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 201 ]; then
        log_success "Document embedded successfully"

        # Check response for status
        if echo "$BODY" | grep -q "success"; then
            log_success "Server confirmed successful embedding"
        fi

        # Try to extract document status
        DOC_STATUS=$(echo "$BODY" | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || true)
        if [ -n "$DOC_STATUS" ]; then
            log_info "Document status: $DOC_STATUS"
        fi
    else
        log_error "Embedding failed with HTTP $HTTP_CODE"
        log_error "Response: $BODY"

        # Common error analysis
        if echo "$BODY" | grep -q "not found"; then
            log_warning "Document not found. Ensure upload completed successfully."
            log_warning "Try using: custom-documents/${FILENAME_WITHOUT_EXT}.txt"
        elif echo "$BODY" | grep -q "embedder"; then
            log_warning "Embedder configuration issue. Check AnythingLLM settings."
        fi

        exit 1
    fi

    echo ""
fi

# ============================================================================
# STEP 3: Verify Document
# ============================================================================

if [ "$UPLOAD_ONLY" -ne 1 ]; then
    log_info "STEP 3: Verification..."

    # Try to get workspace info
    VERIFY_RESPONSE=$(curl -s -X GET \
        "${BASE_URL}/api/v1/workspace/${WORKSPACE_SLUG}" \
        -H "Authorization: Bearer ${API_KEY}" \
        -w "\n%{http_code}")

    HTTP_CODE=$(echo "$VERIFY_RESPONSE" | tail -n 1)
    BODY=$(echo "$VERIFY_RESPONSE" | head -n -1)

    log_debug "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" -eq 200 ]; then
        log_success "Retrieved workspace information"

        # Check if document is in the response
        if echo "$BODY" | grep -q "$FILENAME_WITHOUT_EXT"; then
            log_success "Document found in workspace response!"
        else
            log_warning "Document not found in workspace response"
            log_info "Response: $BODY"
        fi
    else
        log_warning "Could not retrieve workspace info (HTTP $HTTP_CODE)"
        log_debug "Response: $BODY"
    fi

    echo ""
fi

# ============================================================================
# Summary
# ============================================================================

log_info "Test Summary"
echo "============================================"
log_success "Workflow Complete"
echo ""
echo "Document Information:"
echo "  File: $TEST_FILE"
echo "  Location: $DOC_LOCATION"
echo "  Workspace: $WORKSPACE_SLUG"
echo ""
echo "Next Steps:"
echo "  1. Check AnythingLLM UI - document should appear in workspace"
echo "  2. Try querying the workspace with a chat message"
echo "  3. Verify document is embedded by asking content-specific questions"
echo ""
echo "Troubleshooting:"
echo "  - Enable verbose mode with --verbose flag"
echo "  - Check AnythingLLM logs: docker logs -f anythingllm"
echo "  - Verify API key: $API_KEY"
echo "  - Verify workspace exists: $WORKSPACE_SLUG"
echo ""
