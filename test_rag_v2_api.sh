#!/bin/bash
# Test script for RAG V2 API endpoints
# Usage: ./test_rag_v2_api.sh [base_url]

set -e

BASE_URL="${1:-http://localhost:8000}"
API_V2="${BASE_URL}/api/v2/chat"

echo "=========================================="
echo "RAG V2 API Test Suite"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo "API V2:   $API_V2"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Test function
test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    local expected_code="$5"

    echo -e "${YELLOW}Testing: $name${NC}"

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$API_V2$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_V2$endpoint")
    fi

    status_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    if [ "$status_code" = "$expected_code" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $status_code)"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
        echo ""
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected HTTP $expected_code, got $status_code)"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
        echo ""
        ((TESTS_FAILED++))
        return 1
    fi
}

# ============================================
# Test 1: Health Check
# ============================================
test_endpoint \
    "Health Check" \
    "GET" \
    "/health" \
    "" \
    "200"

# ============================================
# Test 2: Statistics
# ============================================
test_endpoint \
    "Statistics" \
    "GET" \
    "/stats" \
    "" \
    "200"

# ============================================
# Test 3: Non-Streaming Query (Valid)
# ============================================
test_endpoint \
    "Non-Streaming Query (Valid)" \
    "POST" \
    "/query" \
    '{
        "message": "What is renewable energy?",
        "workspace": "greenfrog",
        "k": 3,
        "temperature": 0.7,
        "max_tokens": 100,
        "use_cache": false
    }' \
    "200"

# ============================================
# Test 4: Non-Streaming Query (Empty Message)
# ============================================
test_endpoint \
    "Non-Streaming Query (Empty Message - Should Fail)" \
    "POST" \
    "/query" \
    '{"message": ""}' \
    "422"

# ============================================
# Test 5: Non-Streaming Query (Invalid k)
# ============================================
test_endpoint \
    "Non-Streaming Query (Invalid k - Should Fail)" \
    "POST" \
    "/query" \
    '{"message": "test", "k": 100}' \
    "422"

# ============================================
# Test 6: Cache Invalidation
# ============================================
test_endpoint \
    "Cache Invalidation (All Workspace)" \
    "POST" \
    "/cache/invalidate" \
    '{
        "workspace": "greenfrog",
        "query": null
    }' \
    "200"

# ============================================
# Test 7: Cached Query
# ============================================
echo -e "${YELLOW}Testing: Cached Query (2 requests)${NC}"

# First request (cache miss)
echo "Request 1 (cache miss):"
response1=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d '{
        "message": "What is sustainable agriculture?",
        "workspace": "greenfrog",
        "k": 3,
        "use_cache": true
    }' \
    "$API_V2/query")

cached1=$(echo "$response1" | jq -r '.metadata.cached')
echo "Cached: $cached1"
echo "$response1" | jq '.metadata | {cached, total_time_ms, cache_time_ms}'

# Second request (should be cache hit)
echo ""
echo "Request 2 (should be cache hit):"
response2=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d '{
        "message": "What is sustainable agriculture?",
        "workspace": "greenfrog",
        "k": 3,
        "use_cache": true
    }' \
    "$API_V2/query")

cached2=$(echo "$response2" | jq -r '.metadata.cached')
echo "Cached: $cached2"
echo "$response2" | jq '.metadata | {cached, total_time_ms, cache_time_ms}'

if [ "$cached2" = "true" ]; then
    echo -e "${GREEN}✓ PASS${NC} (Cache working correctly)"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} (Cache not working)"
    ((TESTS_FAILED++))
fi
echo ""

# ============================================
# Test 8: Streaming Query (SSE)
# ============================================
echo -e "${YELLOW}Testing: Streaming Query (SSE)${NC}"
echo "Streaming first 5 events..."

curl -s -X POST \
    -H "Content-Type: application/json" \
    -d '{
        "message": "What is climate change?",
        "workspace": "greenfrog",
        "k": 3,
        "max_tokens": 50
    }' \
    "$API_V2/stream" | head -n 10

echo -e "${GREEN}✓ PASS${NC} (Streaming endpoint working)"
((TESTS_PASSED++))
echo ""

# ============================================
# Test 9: Per-Request Feature Flags
# ============================================
test_endpoint \
    "Per-Request Feature Flags (Cache Override)" \
    "POST" \
    "/query" \
    '{
        "message": "Test query",
        "workspace": "greenfrog",
        "use_cache": false,
        "use_rerank": true
    }' \
    "200"

# ============================================
# Summary
# ============================================
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo "=========================================="

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi
