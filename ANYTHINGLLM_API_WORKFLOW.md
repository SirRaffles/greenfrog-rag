# AnythingLLM Document Upload & Embedding API Workflow

## Overview

The AnythingLLM document management system requires a **two-step process**:

1. **Upload** - Convert document to text (stored in `custom-documents/`)
2. **Embed** - Chunk text and create vectors in vector database

Documents don't appear in the workspace until both steps are completed.

---

## Complete API Workflow

### Step 1: Upload Document to System

Upload file to AnythingLLM's document storage (NOT directly to workspace).

**Endpoint:**
```
POST /api/v1/document/upload
```

**Headers:**
```
Authorization: Bearer {API_KEY}
Content-Type: multipart/form-data
```

**Parameters:**
- `file` (required): The file to upload (multipart form field)

**cURL Example:**
```bash
curl -X POST 'http://localhost:3001/api/v1/document/upload' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@/path/to/document.pdf'
```

**Response Example:**
```json
{
  "success": true,
  "document": {
    "id": 123,
    "name": "document.pdf",
    "location": "custom-documents/document.pdf"
  }
}
```

**Important Notes:**
- File is converted to text during upload
- Resulting text file stored as: `custom-documents/{filename_without_ext}.txt`
- For `document.pdf` → `custom-documents/document.txt`
- Upload completes quickly; embedding happens in Step 2

---

### Step 2: Embed Document in Workspace

Move the uploaded document to workspace and create embeddings.

**Endpoint:**
```
POST /api/v1/workspace/{workspace_slug}/update-embeddings
```

**Workspace Slug:** The URL-friendly workspace identifier (e.g., "greenfrog")

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

**cURL Example:**
```bash
curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/update-embeddings' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  -d '{
    "adds": ["custom-documents/document.txt"]
  }'
```

**Response Example:**
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

**What Happens:**
1. Text from `custom-documents/document.txt` is chunked
2. Chunks sent to configured embedder model
3. Vectors generated and stored in vector database
4. Document available in workspace for RAG queries

**Processing Time:**
- Document size dependent (typically seconds to minutes)
- Large documents may take longer

---

## Important: Workspace Slug vs ID

AnythingLLM uses **workspace slug** (not ID) in API endpoints:

| Property | Example | Usage |
|----------|---------|-------|
| **ID** | 1 | Database identifier (internal) |
| **Slug** | "greenfrog" | API endpoints & URLs |
| **Name** | "Green Frog" | Display name |

Use the **slug** in API calls:
```
/api/v1/workspace/greenfrog/update-embeddings  ✓ CORRECT
/api/v1/workspace/1/update-embeddings          ✗ INCORRECT
```

---

## Common Issues & Troubleshooting

### Issue: Documents Uploaded But Not Appearing in Workspace

**Cause:** Step 2 (embedding) not completed

**Solution:** Ensure you:
1. Use correct document path: `custom-documents/filename.txt`
2. Send POST request to `update-embeddings` endpoint
3. Wait for embedding to complete (check logs)

### Issue: "Could not find document" Error

**Causes:**
1. Filename mismatch (case-sensitive)
2. Extension mismatch (usually `.txt` for uploaded documents)
3. Document not uploaded yet

**Solution:**
- Verify exact filename after upload
- Use format: `custom-documents/{filename}.txt`

### Issue: Embedding Fails

**Possible Causes:**
1. Embedder model not configured
2. Network issues downloading embedder
3. CPU doesn't support AVX2 instruction set
4. Out of memory

**Check AnythingLLM logs:**
```bash
docker logs -f anythingllm
```

### Issue: Upload Endpoint Returns 404

**Cause:** Wrong endpoint path

**Common Mistakes:**
- Using `/api/workspace/{slug}/upload` instead of `/api/v1/document/upload`
- Missing `/v1` in path
- Typo in endpoint

**Correct Path:** `/api/v1/document/upload` (global, not workspace-specific)

---

## Complete Workflow Example

### 1. Upload File
```bash
curl -X POST 'http://localhost:3001/api/v1/document/upload' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -F 'file=@/tmp/report.pdf'
```

Response indicates file stored as: `custom-documents/report.txt`

### 2. Wait briefly for text extraction

### 3. Embed in Workspace
```bash
curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/update-embeddings' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json' \
  -d '{
    "adds": ["custom-documents/report.txt"]
  }'
```

### 4. Verify in Workspace
Check AnythingLLM UI or query workspace documents endpoint

---

## Verification Methods

### Method 1: Check AnythingLLM UI
1. Navigate to workspace
2. Look for document in sidebar
3. Document should show "embedded" status

### Method 2: API Query (if available)
```bash
curl 'http://localhost:3001/api/v1/workspace/greenfrog/documents' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA'
```

### Method 3: Test with Chat Query
Send a chat message referencing the document content:
```bash
curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/chat' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "What is the main topic of the report?",
    "mode": "query"
  }'
```

If document is embedded, the response will reference it.

---

## Multiple Documents

To embed multiple documents at once:

```bash
curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/update-embeddings' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json' \
  -d '{
    "adds": [
      "custom-documents/report.txt",
      "custom-documents/document.txt",
      "custom-documents/guide.txt"
    ]
  }'
```

---

## Python Implementation Example

```python
import requests
import json
from pathlib import Path

class AnythingLLMClient:
    def __init__(self, base_url="http://localhost:3001", api_key=""):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}"
        }

    def upload_document(self, file_path):
        """Step 1: Upload document to system storage"""
        url = f"{self.base_url}/api/v1/document/upload"

        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, headers=self.headers, files=files)

        response.raise_for_status()
        result = response.json()

        # Extract the document path
        doc_location = result.get('document', {}).get('location')
        return doc_location

    def embed_in_workspace(self, workspace_slug, document_paths):
        """Step 2: Embed document(s) in workspace"""
        url = f"{self.base_url}/api/v1/workspace/{workspace_slug}/update-embeddings"

        headers = {**self.headers, "Content-Type": "application/json"}
        payload = {"adds": document_paths}

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        return response.json()

    def upload_and_embed(self, file_path, workspace_slug):
        """Complete workflow: upload then embed"""
        # Step 1: Upload
        doc_location = self.upload_document(file_path)
        print(f"Uploaded: {doc_location}")

        # Step 2: Embed
        result = self.embed_in_workspace(workspace_slug, [doc_location])
        print(f"Embedded in workspace: {result.get('message')}")

        return result

# Usage
client = AnythingLLMClient(
    base_url="http://localhost:3001",
    api_key="sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA"
)

# Upload and embed single document
client.upload_and_embed("/tmp/report.pdf", "greenfrog")

# Upload and embed multiple documents
for file in ["/tmp/doc1.pdf", "/tmp/doc2.txt"]:
    doc_loc = client.upload_document(file)
    print(f"Uploaded: {doc_loc}")

# Embed all at once
client.embed_in_workspace("greenfrog", [
    "custom-documents/report.txt",
    "custom-documents/doc1.txt",
    "custom-documents/doc2.txt"
])
```

---

## API Key Requirements

All endpoints require authentication via Authorization header:

```
Authorization: Bearer {API_KEY}
```

Your API Key: `sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA`

To generate or view API keys in AnythingLLM:
1. Go to Settings
2. API Keys section
3. Create or copy existing key

---

## Version Compatibility

This workflow applies to:
- AnythingLLM latest (mintplexlabs/anythingllm:latest)
- All recent versions supporting `/api/v1/` endpoints
- Both Docker and standalone installations

For specific version differences, check: https://github.com/Mintplex-Labs/anything-llm

---

## Related Endpoints

| Purpose | Method | Endpoint |
|---------|--------|----------|
| Upload document | POST | `/api/v1/document/upload` |
| Embed in workspace | POST | `/api/v1/workspace/{slug}/update-embeddings` |
| Remove from workspace | POST | `/api/v1/workspace/{slug}/update-embeddings` (with "removes") |
| Chat with workspace | POST | `/api/v1/workspace/{slug}/chat` |
| Get workspace info | GET | `/api/v1/workspace/{slug}` |

---

## References

- GitHub Issue #1814: Moving uploaded file to workspace
- GitHub Issue #3275: Move to workspace API
- AnythingLLM Official Docs: https://docs.anythingllm.com/
- API Documentation: https://docs.useanything.com/features/api
