# AnythingLLM Document Upload & Embedding API - Research Summary

## Research Completion Date: 2025-11-01

This document summarizes the official AnythingLLM API workflow for uploading and embedding documents in workspaces.

---

## Executive Summary

The reason documents don't appear in your AnythingLLM workspace when uploaded is that **uploading and embedding are two separate API operations that must be called sequentially**:

1. **Upload** (`POST /api/v1/document/upload`) - Creates text file in system storage
2. **Embed** (`POST /api/v1/workspace/{slug}/update-embeddings`) - Chunks text and creates vectors

Your current approach using `POST /api/v1/workspace/{slug}/upload` with files parameter is not the documented API pattern. The correct workflow requires two distinct endpoints.

---

## API Architecture Overview

### Document Processing Pipeline

```
Upload Request
    ↓
File → Text Extraction → custom-documents/{name}.txt
    ↓
Embed Request
    ↓
Text → Chunking → Embedder Model → Vector DB
    ↓
Document Available in Workspace
```

### Key Components

| Component | Purpose | Notes |
|-----------|---------|-------|
| **Upload Endpoint** | File → Text conversion | Global, not workspace-specific |
| **Embed Endpoint** | Text → Vectors → Storage | Workspace-specific |
| **Vector Database** | Stores embeddings | LanceDB, Pinecone, etc. |
| **Embedder Model** | Creates vectors | Configured system-wide |

---

## Complete API Workflow

### Step 1: Upload Document

**Purpose:** Convert document to text and store in system

**Endpoint:** `POST /api/v1/document/upload`

**Headers:**
```
Authorization: Bearer {API_KEY}
Content-Type: multipart/form-data
```

**Form Fields:**
- `file`: Binary file data

**cURL Command:**
```bash
curl -X POST 'http://localhost:3001/api/v1/document/upload' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@/path/to/document.pdf'
```

**Response (Success):**
```json
{
  "success": true,
  "document": {
    "id": 123,
    "name": "document.pdf",
    "location": "custom-documents/document.txt"
  }
}
```

**Response (Error):**
```json
{
  "error": "File upload failed"
}
```

**Status Codes:**
- `200, 201` - Success
- `400` - Bad request (invalid file)
- `401` - Unauthorized (invalid API key)
- `413` - Payload too large
- `500` - Server error

**Important Notes:**
- File location is: `custom-documents/{filename_without_extension}.txt`
- Original file extension doesn't matter (PDF→TXT, DOCX→TXT, etc.)
- Upload completes quickly; text extraction is fast
- Returned location must be used in Step 2

---

### Step 2: Embed in Workspace

**Purpose:** Chunk text and create embeddings for RAG

**Endpoint:** `POST /api/v1/workspace/{workspace_slug}/update-embeddings`

**Workspace Slug:** URL-friendly identifier (e.g., "greenfrog", not workspace ID)

**Headers:**
```
Authorization: Bearer {API_KEY}
Content-Type: application/json
Accept: application/json
```

**Request Body:**
```json
{
  "adds": [
    "custom-documents/document.txt"
  ]
}
```

**cURL Command:**
```bash
curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/update-embeddings' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json' \
  -d '{
    "adds": ["custom-documents/document.txt"]
  }'
```

**Response (Success):**
```json
{
  "workspace": {
    "id": 1,
    "name": "greenfrog",
    "slug": "greenfrog",
    "documents": [
      {
        "name": "document.txt",
        "location": "custom-documents/document.txt",
        "status": "embedded"
      }
    ]
  },
  "message": "Workspace updated successfully"
}
```

**Response (Error - Document Not Found):**
```json
{
  "error": "Document not found at custom-documents/document.txt"
}
```

**Response (Error - Embedder Not Configured):**
```json
{
  "error": "Embedder model not configured"
}
```

**Status Codes:**
- `200, 201` - Success
- `400` - Bad request (invalid path, embedder not set)
- `401` - Unauthorized (invalid API key)
- `404` - Document or workspace not found
- `500` - Server error (embedder issues, network)

**Processing Notes:**
- Text chunking: Configurable chunk size and overlap
- Embedding: Sent to configured embedder (local or remote)
- Storage: Vectors stored in vector database under workspace namespace
- Duration: Depends on document size (seconds to minutes)

**What Happens Internally:**
1. Retrieves text from `custom-documents/document.txt`
2. Applies TextSplitter to chunk content
3. For each chunk: generates embedding vector
4. Stores vectors in vector DB with metadata
5. Creates document_vectors mappings in database
6. Returns updated workspace with document status

---

## Critical Details

### Document Path Format

```
Upload Response: custom-documents/filename.txt
Embed Input:    "custom-documents/filename.txt"  (string in "adds" array)
```

**Examples:**
- Input: `document.pdf` → Output: `custom-documents/document.txt`
- Input: `my_file.docx` → Output: `custom-documents/my_file.txt`
- Input: `data.json` → Output: `custom-documents/data.txt`

### Workspace Identification

```
API Endpoint Uses:  workspace SLUG
Database Uses:      workspace ID
UI Shows:           workspace NAME

Example:
  ID:   1
  Slug: "greenfrog"
  Name: "Green Frog"

  Correct Endpoint:   /api/v1/workspace/greenfrog/...
  Incorrect:          /api/v1/workspace/1/...
```

### Authentication

```
Header Format: Authorization: Bearer {API_KEY}
Your Key:      sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA

All endpoints require this header.
401 error means invalid/missing key.
```

---

## Error Analysis

### Common Error: "Document not found"

**Cause:** Using wrong document path in embed step

**Example:**
- Upload returns: `custom-documents/myfile.txt`
- Embed sends: `custom-documents/myfile.pdf` ← WRONG

**Solution:**
- Always use path exactly as returned from upload
- Document extension is always `.txt` (not original extension)

### Common Error: Documents Not Appearing

**Cause:** Skipping embed step entirely

**Checklist:**
1. [ ] Call `/api/v1/document/upload` first
2. [ ] Get location from response
3. [ ] Wait 1-2 seconds
4. [ ] Call `/api/v1/workspace/{slug}/update-embeddings`
5. [ ] Both calls must succeed

### Common Error: Embedding Fails (500 Error)

**Possible Causes:**
1. Embedder model not configured
2. Embedder download blocked by firewall
3. CPU doesn't support AVX2
4. Insufficient memory
5. Network issues

**Check Logs:**
```bash
docker logs -f anythingllm
# Look for: embedder, download, or network errors
```

### Common Error: 404 on Upload

**Cause:** Wrong endpoint

**Wrong:** `/api/workspace/{slug}/upload`
**Correct:** `/api/v1/document/upload`

The upload endpoint is global, not workspace-specific.

---

## Workspace Slug vs ID Clarification

AnythingLLM workspaces have THREE identifiers:

| Property | Type | Example | Usage |
|----------|------|---------|-------|
| **ID** | Integer | `1` | Internal database reference |
| **Slug** | String | `"greenfrog"` | URL-friendly, used in API routes |
| **Name** | String | `"Green Frog"` | Human-readable display name |

**API Uses Slug:**
```
/api/v1/workspace/greenfrog/update-embeddings      ✓
/api/v1/workspace/1/update-embeddings              ✗
/api/v1/workspace/Green%20Frog/update-embeddings   ✗
```

**Finding Workspace Slug:**
1. UI: Look at workspace URL
2. API: Call GET `/api/v1/workspace/{slug}` endpoint
3. Direct: Workspace slug is usually lowercase with hyphens

---

## Multiple Document Embedding

To embed multiple documents in one operation:

```bash
curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/update-embeddings' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json' \
  -d '{
    "adds": [
      "custom-documents/document1.txt",
      "custom-documents/document2.txt",
      "custom-documents/document3.txt"
    ]
  }'
```

**Process:**
1. All documents embedded in single operation
2. No need to call embed for each document
3. All will be processed concurrently
4. Response shows all document statuses

---

## Verification Methods

### Method 1: AnythingLLM UI
1. Navigate to workspace
2. Check sidebar for documents
3. Look for "embedded" status badge

### Method 2: API Query (GET Workspace)
```bash
curl -X GET 'http://localhost:3001/api/v1/workspace/greenfrog' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA'
```

Look for document in `documents` array.

### Method 3: Test with Chat
```bash
curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/chat' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "What is in the document?",
    "mode": "query"
  }'
```

If document is embedded, LLM will reference it.

---

## Implementation Guide

### Bash/cURL (Simple)
See: `QUICK_API_REFERENCE.md`

### Bash/cURL (Automated)
See: `test-anythingllm-api.sh` - Automated test script with error handling

### Python
See: `anythingllm_client.py` - Full-featured Python client

---

## Source Information

### Official Sources Consulted
1. **GitHub Issue #1814** - Moving uploaded file to workspace
2. **GitHub Issue #3275** - Move to workspace API issues
3. **DeepWiki API Reference** - Architecture and endpoint documentation
4. **AnythingLLM Official Docs** - General document workflow

### Key Findings
- Two-step workflow is intentional design
- Upload and embed are separate concerns
- Document path format is strict: `custom-documents/{name}.txt`
- Workspace slug (not ID) required in API routes
- All operations are async, may take seconds to minutes

---

## Your Configuration

| Setting | Value |
|---------|-------|
| Instance URL | `http://localhost:3001` |
| Workspace | `greenfrog` |
| API Key | `sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA` |

---

## Files Provided

1. **ANYTHINGLLM_API_WORKFLOW.md** (Detailed)
   - Complete workflow documentation
   - All endpoint specifications
   - Python implementation example
   - Troubleshooting guide

2. **QUICK_API_REFERENCE.md** (Quick)
   - One-page reference
   - Two key curl commands
   - Common issues table

3. **test-anythingllm-api.sh** (Automated Testing)
   - Full workflow test script
   - Error handling and verification
   - Verbose debugging output
   - Usage: `./test-anythingllm-api.sh --create-test-file`

4. **anythingllm_client.py** (Python Library)
   - Reusable Python client
   - Command-line interface
   - Error handling
   - Batch operations support

---

## Next Steps

1. **Test the Workflow**
   ```bash
   cd /volume1/docker/greenfrog-rag
   chmod +x test-anythingllm-api.sh
   ./test-anythingllm-api.sh --create-test-file --verbose
   ```

2. **Verify Documents Appear**
   - Check AnythingLLM UI
   - Documents should appear in workspace sidebar
   - Status should show "embedded"

3. **Test RAG Query**
   - Ask the workspace a question about the document content
   - If embedded, LLM should reference the document

4. **For Production Use**
   - Use Python client: `anythingllm_client.py`
   - Integrate into your pipeline
   - Handle errors appropriately

---

## Important Notes

1. **Workspace Slug is Critical**
   - Must use slug, not ID
   - If unsure, check workspace URL in UI
   - Slug is usually lowercase with hyphens

2. **Document Path Must Match**
   - Exactly as returned from upload
   - Always ends with `.txt` (even if original was PDF)
   - Case-sensitive on Linux

3. **Processing Time Varies**
   - Small files: seconds
   - Large files: minutes
   - Network-dependent for remote embedders

4. **Embedder Must Be Configured**
   - Check AnythingLLM settings
   - System-wide setting (not per-workspace)
   - Embedding will fail if not configured

---

## Summary

The correct workflow is:

1. **POST** `/api/v1/document/upload` with file
2. Get document location: `custom-documents/filename.txt`
3. **POST** `/api/v1/workspace/greenfrog/update-embeddings` with location
4. Wait for embedding to complete
5. Document appears in workspace

This is the official, documented approach across all AnythingLLM versions and deployment types (Docker, standalone, cloud).
