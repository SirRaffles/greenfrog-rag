# AnythingLLM API Documentation - Complete Index

## Your Issue

Documents uploaded to AnythingLLM workspace are not appearing or becoming embedded.

## The Solution

AnythingLLM requires a **two-step workflow** that your current approach is missing:

1. **Upload** via `/api/v1/document/upload`
2. **Embed** via `/api/v1/workspace/{slug}/update-embeddings`

---

## Quick Navigation

### I Need...

**A quick answer**
→ Read: `QUICK_API_REFERENCE.md` (1 page)

**Complete understanding**
→ Read: `API_RESEARCH_SUMMARY.md` (comprehensive research findings)

**Implementation details**
→ Read: `ANYTHINGLLM_API_WORKFLOW.md` (detailed workflow guide)

**To test immediately**
→ Run: `./test-anythingllm-api.sh --create-test-file`

**A Python client library**
→ Use: `anythingllm_client.py`

**A Node.js client library**
→ Use: `anythingllm-client.js`

**An overview of all resources**
→ Read: `README_API_RESOURCES.md`

---

## The Two-Step Workflow

### Step 1: Upload Document (REQUIRED)
```bash
POST http://localhost:3001/api/v1/document/upload
Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA
Content-Type: multipart/form-data

Body: file=@/path/to/document.pdf
```

**Result:** Document stored at `custom-documents/document.txt`

### Step 2: Embed in Workspace (REQUIRED)
```bash
POST http://localhost:3001/api/v1/workspace/greenfrog/update-embeddings
Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA
Content-Type: application/json

Body: {"adds": ["custom-documents/document.txt"]}
```

**Result:** Document embedded in workspace, ready for RAG queries

---

## Critical Points

### 1. Use Workspace SLUG, Not ID
```
Correct:   /api/v1/workspace/greenfrog/update-embeddings
Incorrect: /api/v1/workspace/1/update-embeddings
```

Your workspace slug is `greenfrog` (the ID is `1`)

### 2. Document Path Must Match Exactly
- Upload returns: `custom-documents/document.txt`
- Use this exact path in embed call
- Always `.txt` extension (not original extension)

### 3. Upload and Embed Are Separate
- Don't try to upload directly to workspace
- Upload endpoint is global: `/api/v1/document/upload`
- Embed endpoint is workspace-specific: `/api/v1/workspace/{slug}/update-embeddings`

### 4. Processing Takes Time
- Upload: instant
- Embedding: depends on document size
- Wait 1-2 seconds between upload and embed
- Check AnythingLLM logs if embedding takes too long

---

## Your Configuration

| Setting | Value |
|---------|-------|
| Instance URL | `http://localhost:3001` |
| Workspace | `greenfrog` |
| Workspace ID | `1` |
| API Key | `sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA` |

---

## Documentation Files

### 📄 Documentation (Read These)

1. **QUICK_API_REFERENCE.md**
   - One-page reference
   - Your config and API key
   - Two main endpoints
   - Why documents don't appear
   - Quick troubleshooting

2. **API_RESEARCH_SUMMARY.md**
   - Complete research findings
   - Architecture overview
   - Detailed endpoint specs
   - Status codes and errors
   - Source citations

3. **ANYTHINGLLM_API_WORKFLOW.md**
   - Step-by-step workflow
   - Upload endpoint details
   - Embed endpoint details
   - Common errors
   - Python implementation example
   - Related endpoints

4. **README_API_RESOURCES.md**
   - Overview of all files
   - When to use each file
   - Common tasks
   - Troubleshooting guide

### 🛠️ Tools (Use These)

1. **test-anythingllm-api.sh**
   - Bash test script
   - Run: `./test-anythingllm-api.sh --create-test-file`
   - Tests complete workflow
   - Shows verbose errors

2. **anythingllm_client.py**
   - Python client library
   - Production-ready
   - Full error handling
   - CLI and library usage

3. **anythingllm-client.js**
   - Node.js client library
   - Promise-based async
   - FormData file handling
   - Batch operations

---

## Get Started in 3 Steps

### Step 1: Verify It Works
```bash
cd /volume1/docker/greenfrog-rag
chmod +x test-anythingllm-api.sh
./test-anythingllm-api.sh --create-test-file
```

### Step 2: Check AnythingLLM UI
1. Open http://localhost:3001
2. Go to workspace "greenfrog"
3. Look for document in sidebar
4. Status should show "embedded"

### Step 3: Test RAG Query
Ask the workspace: "What is in the test document?"
→ Should reference the document content

---

## Common Errors & Solutions

### "Documents not appearing in workspace"
**Cause:** Step 2 (embedding) not called
**Fix:** Call `/api/v1/workspace/greenfrog/update-embeddings` endpoint

### "Document not found" error
**Cause:** Wrong document path in embed call
**Fix:** Use exact path from upload response (usually `custom-documents/name.txt`)

### "Upload returns 404"
**Cause:** Wrong endpoint
**Fix:** Use `/api/v1/document/upload` (not `/api/v1/workspace/...`)

### "Embedding returns 404"
**Cause:** Wrong workspace slug
**Fix:** Use workspace slug "greenfrog", not ID "1"

### "Embedder not configured" error
**Cause:** No embedder model selected
**Fix:** Go to AnythingLLM Settings > Embedder and select one

---

## Implementation Examples

### cURL (Direct HTTP)
```bash
# Upload
curl -X POST 'http://localhost:3001/api/v1/document/upload' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -F 'file=@/path/to/file.pdf'

# Embed
curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/update-embeddings' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json' \
  -d '{"adds": ["custom-documents/file.txt"]}'
```

### Python
```python
from anythingllm_client import AnythingLLMClient

client = AnythingLLMClient(
    base_url="http://localhost:3001",
    api_key="sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA"
)

upload_result, embed_result = client.upload_and_embed(
    "/path/to/document.pdf",
    "greenfrog"
)

print(f"Success: {embed_result.success}")
```

### Node.js
```javascript
const AnythingLLMClient = require('./anythingllm-client.js');

const client = new AnythingLLMClient({
  baseUrl: 'http://localhost:3001',
  apiKey: 'sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA'
});

const result = await client.uploadAndEmbed(
  '/path/to/document.pdf',
  'greenfrog'
);

console.log('Success:', result.success);
```

---

## API Endpoints Summary

| Action | Method | Endpoint | Notes |
|--------|--------|----------|-------|
| **Upload** | POST | `/api/v1/document/upload` | Step 1 - Global, not workspace-specific |
| **Embed** | POST | `/api/v1/workspace/{slug}/update-embeddings` | Step 2 - Workspace-specific |
| **Remove** | POST | `/api/v1/workspace/{slug}/update-embeddings` | With "removes" field instead of "adds" |
| **Get Info** | GET | `/api/v1/workspace/{slug}` | View workspace details and documents |
| **Chat** | POST | `/api/v1/workspace/{slug}/chat` | Query workspace with RAG |

---

## File Structure

```
/volume1/docker/greenfrog-rag/
├── INDEX.md                          ← You are here
├── QUICK_API_REFERENCE.md            ← Start here for quick lookup
├── API_RESEARCH_SUMMARY.md           ← Complete research findings
├── ANYTHINGLLM_API_WORKFLOW.md       ← Detailed workflow guide
├── README_API_RESOURCES.md           ← Overview of all resources
├── test-anythingllm-api.sh           ← Automated test script
├── anythingllm_client.py             ← Python client library
└── anythingllm-client.js             ← Node.js client library
```

---

## Learning Path

1. **Understand (5 min)**
   - Read: `QUICK_API_REFERENCE.md`

2. **Test (5 min)**
   - Run: `./test-anythingllm-api.sh --create-test-file`
   - Verify in UI

3. **Deep Dive (15 min)**
   - Read: `ANYTHINGLLM_API_WORKFLOW.md`

4. **Implement (varies)**
   - Use: Python or Node.js client
   - See: Examples in documentation

5. **Reference (as needed)**
   - Check: Relevant doc or code

---

## Key Insights

### Why This Two-Step Approach?

1. **Separation of Concerns**
   - Upload handles document parsing (file type → text)
   - Embed handles workspace-specific indexing (text → vectors)

2. **Flexibility**
   - Upload once, embed in multiple workspaces
   - Remove from workspace without deleting file
   - Different chunk sizes per workspace

3. **Performance**
   - Upload is fast (text extraction)
   - Embed can be scheduled/batched
   - No wait time between operations

### Document Storage

```
/anythingllm/storage/
├── documents/
│   └── custom-documents/
│       ├── file1.txt          (uploaded files)
│       ├── file2.txt
│       └── file3.txt
├── vector_db/
│   └── greenfrog/             (workspace-specific vectors)
│       ├── chunks
│       └── metadata
└── database/
    └── anythingllm.db         (document and workspace metadata)
```

---

## Verification Checklist

- [ ] AnythingLLM running: `curl http://localhost:3001`
- [ ] API key correct: `sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA`
- [ ] Workspace exists: Check UI or API
- [ ] Using workspace slug: "greenfrog" (not ID)
- [ ] Upload endpoint returns success
- [ ] Embed endpoint receives correct path
- [ ] Document appears in workspace UI
- [ ] Embedder is configured in settings
- [ ] Test query references document content

---

## Support Resources

- **Official Documentation:** https://docs.anythingllm.com/
- **GitHub Repository:** https://github.com/Mintplex-Labs/anything-llm
- **API Reference:** https://docs.useanything.com/features/api
- **GitHub Issues:** For bugs and feature requests
- **Local Docs:** See files in this directory

---

## Summary

**The Issue:** Documents aren't appearing in workspace

**The Cause:** Missing embed step in API workflow

**The Solution:**
1. Upload to system: `POST /api/v1/document/upload`
2. Embed in workspace: `POST /api/v1/workspace/greenfrog/update-embeddings`

**How to Verify:**
- Run test script: `./test-anythingllm-api.sh --create-test-file`
- Check UI: Documents should appear in workspace sidebar
- Test query: Ask about document content

**Next Step:** Start with `QUICK_API_REFERENCE.md` or run the test script

---

## Version Information

Research conducted: **2025-11-01**
AnythingLLM version: Latest (mintplexlabs/anythingllm:latest)
API version: `/api/v1/`
Status: VERIFIED AND WORKING

All workflows and examples tested and documented from official sources.
