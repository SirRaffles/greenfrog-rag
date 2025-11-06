#!/bin/bash

################################################################################
# AnythingLLM API - cURL Command Examples
#
# Copy and paste these commands into your terminal.
# Replace paths and workspace names as needed.
#
# Configuration:
#   Base URL: http://localhost:3001
#   Workspace: greenfrog
#   API Key: sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA
################################################################################

# ============================================================================
# BASIC WORKFLOW - Upload and Embed a Document
# ============================================================================

# 1. UPLOAD DOCUMENT
# ==================
# Uploads a file and converts it to text
# Creates: custom-documents/{filename}.txt

echo "=== STEP 1: Upload Document ==="
curl -X POST 'http://localhost:3001/api/v1/document/upload' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@/path/to/document.pdf'

echo ""
echo "Copy the 'location' value from the response for step 2"
echo ""

# 2. EMBED IN WORKSPACE
# =====================
# Embeds the document in the workspace
# Makes it available for RAG queries

echo "=== STEP 2: Embed in Workspace ==="
curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/update-embeddings' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json' \
  -d '{
    "adds": ["custom-documents/document.txt"]
  }'

echo ""

# ============================================================================
# COMMON VARIATIONS
# ============================================================================

# UPLOAD MULTIPLE FILES
# =======================
# Steps 1 & 2 but with multiple documents

echo "=== Upload and Embed Multiple Documents ==="

# Upload first document
echo "Uploading file 1..."
RESPONSE1=$(curl -s -X POST 'http://localhost:3001/api/v1/document/upload' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -F 'file=@/path/to/document1.pdf')
DOC1=$(echo $RESPONSE1 | grep -o '"location":"[^"]*"' | cut -d'"' -f4)

# Upload second document
echo "Uploading file 2..."
RESPONSE2=$(curl -s -X POST 'http://localhost:3001/api/v1/document/upload' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -F 'file=@/path/to/document2.pdf')
DOC2=$(echo $RESPONSE2 | grep -o '"location":"[^"]*"' | cut -d'"' -f4)

# Embed both
echo "Embedding both documents..."
curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/update-embeddings' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json' \
  -d "{
    \"adds\": [\"$DOC1\", \"$DOC2\"]
  }"

echo ""

# ============================================================================
# VERIFICATION & INSPECTION
# ============================================================================

# GET WORKSPACE INFO
# ===================
# View all documents in workspace and their status

echo "=== Get Workspace Information ==="
curl -X GET 'http://localhost:3001/api/v1/workspace/greenfrog' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json'

echo ""

# ============================================================================
# DOCUMENT MANAGEMENT
# ============================================================================

# REMOVE DOCUMENT FROM WORKSPACE
# ================================
# Remove a document but keep the file in storage

echo "=== Remove Document from Workspace ==="
curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/update-embeddings' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json' \
  -d '{
    "removes": ["custom-documents/document.txt"]
  }'

echo ""

# ============================================================================
# RAG QUERYING
# ============================================================================

# CHAT WITH WORKSPACE
# ====================
# Ask a question about the documents in the workspace

echo "=== Chat with Workspace ==="
curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/chat' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "What is the main topic of the document?",
    "mode": "query"
  }'

echo ""

# ============================================================================
# DEBUGGING & DIAGNOSTICS
# ============================================================================

# TEST API KEY
# =============
# Verify your API key is working

echo "=== Test API Key ==="
curl -X GET 'http://localhost:3001/api/v1/workspace/greenfrog' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA'

echo ""

# CHECK ANYTHINGLLM IS RUNNING
# ==============================
# Basic connectivity test

echo "=== Check AnythingLLM Health ==="
curl -s -X GET 'http://localhost:3001' | head -20

echo ""

# ============================================================================
# READY-TO-USE TEMPLATES
# ============================================================================

# Copy and paste these for your specific use case

cat << 'EOF'

=== TEMPLATE 1: Upload and Embed a File ===

# 1. Upload the file
curl -X POST 'http://localhost:3001/api/v1/document/upload' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -F 'file=@YOUR_FILE_PATH_HERE'

# 2. Copy the 'location' value from the response
# 3. Paste it into the next command:

curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/update-embeddings' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json' \
  -d '{"adds": ["PASTE_LOCATION_HERE"]}'


=== TEMPLATE 2: Upload and Embed in Different Workspace ===

# Change "greenfrog" to your workspace name:

curl -X POST 'http://localhost:3001/api/v1/document/upload' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -F 'file=@YOUR_FILE_PATH_HERE'

curl -X POST 'http://localhost:3001/api/v1/workspace/YOUR_WORKSPACE/update-embeddings' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json' \
  -d '{"adds": ["custom-documents/YOUR_FILE_NAME.txt"]}'


=== TEMPLATE 3: Query the Workspace ===

curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/chat' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "YOUR_QUESTION_HERE",
    "mode": "query"
  }'


=== TEMPLATE 4: Check If Document Is Embedded ===

curl -X GET 'http://localhost:3001/api/v1/workspace/greenfrog' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' | jq '.documents'


=== TEMPLATE 5: Remove Document from Workspace ===

curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/update-embeddings' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json' \
  -d '{"removes": ["custom-documents/FILE_NAME.txt"]}'

EOF

echo ""
echo "=== Tips ==="
echo ""
echo "1. Always do UPLOAD before EMBED"
echo "2. Use the 'location' from upload response in embed call"
echo "3. Document path is always: custom-documents/{filename}.txt"
echo "4. Replace workspace name 'greenfrog' with your workspace"
echo "5. API key: sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA"
echo ""
echo "For JSON parsing in bash, install jq:"
echo "  sudo apt-get install jq"
echo ""
echo "Then use:"
echo "  curl ... | jq '.document.location'"
echo ""
