# AnythingLLM API - Complete Documentation Package

## Overview

This directory contains comprehensive documentation and tools for uploading and embedding documents in AnythingLLM workspaces via the API.

**Key Finding:** Documents require a two-step workflow:
1. Upload via `/api/v1/document/upload`
2. Embed via `/api/v1/workspace/{slug}/update-embeddings`

---

## Documentation Files

### 1. API_RESEARCH_SUMMARY.md
**Complete research findings and API documentation**

- Executive summary of the issue
- Complete API architecture
- Detailed endpoint specifications
- Status codes and error handling
- Workspace slug vs ID clarification
- Multiple document embedding
- Verification methods
- Source citations

**When to use:** Understand the complete picture and detailed API specs

---

### 2. ANYTHINGLLM_API_WORKFLOW.md
**Comprehensive workflow guide**

- Overview of the two-step process
- Step 1: Upload Document (complete endpoint details)
- Step 2: Embed Document (complete endpoint details)
- Important notes about paths and authentication
- Common issues and troubleshooting
- Multiple document examples
- Complete Python implementation example
- Related endpoints reference

**When to use:** Learn how to implement the workflow in detail

---

### 3. QUICK_API_REFERENCE.md
**One-page quick reference**

- Your configuration (URL, workspace, API key)
- The two-step workflow in condensed form
- Why documents don't appear (quick troubleshooting)
- Common endpoints table
- Key points to remember
- Troubleshooting checklist

**When to use:** Quick lookup while implementing

---

## Implementation Tools

### 4. test-anythingllm-api.sh
**Automated test script in Bash**

Features:
- Complete workflow testing (upload + embed)
- Automatic test document creation
- Error handling and verbose debugging
- Verification of results
- Configuration options via flags
- Progress reporting

Usage:
```bash
chmod +x test-anythingllm-api.sh

# Full workflow with test file
./test-anythingllm-api.sh --create-test-file

# Custom workspace
./test-anythingllm-api.sh --workspace myworkspace --create-test-file

# Verbose debugging
./test-anythingllm-api.sh --create-test-file --verbose

# Upload only
./test-anythingllm-api.sh --upload-only --file /path/to/file.pdf

# Embed only
./test-anythingllm-api.sh --embed-only
```

**When to use:** Quick testing without coding

---

### 5. anythingllm_client.py
**Full-featured Python client library**

Features:
- Object-oriented design
- Complete error handling
- Logging with debug levels
- Batch operations (multiple documents)
- Verification methods
- Type hints and docstrings
- Command-line interface

Usage as Library:
```python
from anythingllm_client import AnythingLLMClient

client = AnythingLLMClient(
    base_url="http://localhost:3001",
    api_key="sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA"
)

# Upload and embed
upload_result, embed_result = client.upload_and_embed(
    "/path/to/document.pdf",
    "greenfrog"
)

print(f"Success: {embed_result.success}")
print(f"Message: {embed_result.message}")
```

Usage as CLI:
```bash
# Upload file
python3 anythingllm_client.py upload --file /path/to/file.pdf

# Complete workflow
python3 anythingllm_client.py upload-embed --file /path/to/file.pdf

# Verify document
python3 anythingllm_client.py verify --file document.pdf
```

**When to use:** Building production integrations

---

### 6. anythingllm-client.js
**Full-featured Node.js/JavaScript client**

Features:
- ES6/modern JavaScript
- Promise-based async/await
- FormData file handling
- Batch operations
- Logging system
- Error handling
- Example usage included

Usage:
```javascript
const AnythingLLMClient = require('./anythingllm-client.js');

const client = new AnythingLLMClient({
  baseUrl: 'http://localhost:3001',
  apiKey: 'sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA'
});

// Upload and embed
const result = await client.uploadAndEmbed(
  '/path/to/document.pdf',
  'greenfrog'
);

console.log('Success:', result.success);
console.log('Message:', result.embed.message);
```

**When to use:** Node.js backend or web integrations

---

## Configuration

Your AnythingLLM Setup:
```
Instance URL:  http://localhost:3001
Workspace:     greenfrog
API Key:       sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA
```

These are pre-configured in the test script and client libraries.

---

## Quick Start

### 1. Test Everything Works
```bash
cd /volume1/docker/greenfrog-rag
chmod +x test-anythingllm-api.sh
./test-anythingllm-api.sh --create-test-file
```

Expected output:
- Document uploaded successfully
- Document embedded successfully
- Test complete message

### 2. Verify in AnythingLLM UI
- Open http://localhost:3001
- Go to workspace "greenfrog"
- Should see test document in sidebar
- Status should show "embedded"

### 3. Test RAG Query
- Ask the workspace: "What is in the test document?"
- LLM should reference the document content

### 4. Use in Your Code

**Python:**
```bash
pip install requests
python3 -c "
from anythingllm_client import AnythingLLMClient
client = AnythingLLMClient(api_key='sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA')
client.upload_and_embed('/path/to/doc.pdf', 'greenfrog')
"
```

**Node.js:**
```bash
npm install form-data
node -e "
const Client = require('./anythingllm-client.js');
const client = new Client({apiKey: 'sk-...'});
client.uploadAndEmbed('/path/to/doc.pdf', 'greenfrog');
"
```

**Bash/cURL:**
```bash
# See QUICK_API_REFERENCE.md for direct curl commands
```

---

## The API Workflow

### Step 1: Upload
```
POST /api/v1/document/upload
Authorization: Bearer {API_KEY}
Content-Type: multipart/form-data

Body: file=@document.pdf
Response: { document: { location: "custom-documents/document.txt" } }
```

### Step 2: Embed
```
POST /api/v1/workspace/greenfrog/update-embeddings
Authorization: Bearer {API_KEY}
Content-Type: application/json

Body: { "adds": ["custom-documents/document.txt"] }
Response: { workspace: {...}, message: "Workspace updated successfully" }
```

---

## File Locations

All files are in: `/volume1/docker/greenfrog-rag/`

| File | Type | Purpose |
|------|------|---------|
| API_RESEARCH_SUMMARY.md | Doc | Complete research findings |
| ANYTHINGLLM_API_WORKFLOW.md | Doc | Detailed workflow guide |
| QUICK_API_REFERENCE.md | Doc | One-page quick reference |
| test-anythingllm-api.sh | Script | Bash testing script |
| anythingllm_client.py | Code | Python client library |
| anythingllm-client.js | Code | Node.js client library |
| README_API_RESOURCES.md | Doc | This file |

---

## Common Tasks

### Upload a Single Document
```bash
./test-anythingllm-api.sh --file /path/to/document.pdf
```

### Upload Multiple Documents
```python
from anythingllm_client import AnythingLLMClient

client = AnythingLLMClient(api_key="sk-...")
result = client.upload_multiple(
    ["/path/doc1.pdf", "/path/doc2.pdf"],
    "greenfrog"
)
```

### Verify Document is Embedded
```bash
curl -X GET 'http://localhost:3001/api/v1/workspace/greenfrog' \
  -H 'Authorization: Bearer sk-...'
```

### Remove Document from Workspace
```bash
curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/update-embeddings' \
  -H 'Authorization: Bearer sk-...' \
  -H 'Content-Type: application/json' \
  -d '{"removes": ["custom-documents/document.txt"]}'
```

### Check AnythingLLM Logs
```bash
docker logs -f anythingllm
```

---

## Troubleshooting

### Documents Not Appearing in Workspace

**Check:**
1. Both API calls succeeded (check script output)
2. Using correct workspace slug (not ID)
3. Using correct document path (`custom-documents/name.txt`)
4. Embedder is configured (check AnythingLLM Settings)
5. Wait for embedding to complete (size dependent)

**Debug:**
```bash
./test-anythingllm-api.sh --create-test-file --verbose
# Shows detailed HTTP requests and responses
```

### Upload Returns 404

**Issue:** Using wrong endpoint
- Wrong: `/api/workspace/{slug}/upload`
- Right: `/api/v1/document/upload`

### Embedding Returns 404

**Issues:**
- Wrong workspace slug
- Document path doesn't exist
- Typo in path

**Fix:**
- Verify workspace exists: Check UI or API
- Use exact path returned from upload
- Remember `.txt` extension (not original)

### Embedder Configuration Error

**Issue:** "Embedder model not configured"

**Fix:**
1. Open AnythingLLM UI
2. Settings > Embedder
3. Select an embedder (local or remote)
4. Retry embedding

---

## API Reference Quick Links

Full endpoint documentation in: **ANYTHINGLLM_API_WORKFLOW.md**

Key endpoints:
- Upload: `POST /api/v1/document/upload`
- Embed: `POST /api/v1/workspace/{slug}/update-embeddings`
- Info: `GET /api/v1/workspace/{slug}`
- Chat: `POST /api/v1/workspace/{slug}/chat`

---

## Python Client Methods

```python
client = AnythingLLMClient(base_url="...", api_key="...")

# Upload single document
location = client.upload_document("/path/to/file.pdf")

# Embed in workspace
result = client.embed_in_workspace("greenfrog", ["custom-documents/file.txt"])

# Upload and embed (complete workflow)
upload_result, embed_result = client.upload_and_embed("/path/to/file.pdf", "greenfrog")

# Upload multiple documents
result = client.upload_multiple(["/path/doc1.pdf", "/path/doc2.pdf"], "greenfrog")

# Get workspace info
info = client.get_workspace_info("greenfrog")

# Verify document is embedded
is_embedded = client.verify_document_embedded("greenfrog", "file.txt")
```

---

## JavaScript Client Methods

```javascript
const client = new AnythingLLMClient({
  baseUrl: 'http://localhost:3001',
  apiKey: 'sk-...'
});

// Upload single document
const location = await client.uploadDocument("/path/to/file.pdf");

// Embed in workspace
const result = await client.embedInWorkspace("greenfrog", ["custom-documents/file.txt"]);

// Upload and embed (complete workflow)
const result = await client.uploadAndEmbed("/path/to/file.pdf", "greenfrog");

// Upload multiple documents
const result = await client.uploadMultiple(["/path/doc1.pdf", "/path/doc2.pdf"], "greenfrog");

// Get workspace info
const info = await client.getWorkspaceInfo("greenfrog");

// Verify document is embedded
const isEmbedded = await client.verifyDocumentEmbedded("greenfrog", "file.txt");
```

---

## Next Steps

1. **Test:** Run `./test-anythingllm-api.sh --create-test-file`
2. **Verify:** Check AnythingLLM UI for document
3. **Integrate:** Use Python or Node.js client in your code
4. **Automate:** Set up scheduled uploads for your workflow

---

## Support & Documentation

- **Official Docs:** https://docs.anythingllm.com/
- **GitHub:** https://github.com/Mintplex-Labs/anything-llm
- **Local Docs:** View `/volume1/docker/greenfrog-rag/ANYTHINGLLM_API_WORKFLOW.md`

---

## Summary

This package provides everything needed to upload and embed documents in AnythingLLM:

- Documentation: Complete API reference and workflow guides
- Testing: Automated scripts to verify functionality
- Implementation: Production-ready Python and JavaScript clients
- Examples: Pre-configured for your setup (localhost:3001, greenfrog workspace)

Start with `QUICK_API_REFERENCE.md` for a quick overview, then consult specific files as needed.
