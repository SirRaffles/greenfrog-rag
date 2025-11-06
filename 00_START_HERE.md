# AnythingLLM API - START HERE

## Your Problem

You're trying to upload documents to AnythingLLM workspace via API, but documents aren't appearing or aren't getting embedded.

**Current approach:** `POST /api/v1/workspace/{slug}/upload` with files parameter

**Status:** This endpoint doesn't exist or isn't the correct API pattern.

---

## The Solution

AnythingLLM **requires a two-step workflow**:

### Step 1: Upload Document
```bash
POST /api/v1/document/upload
```
Converts your file to text and stores it in system (creates `custom-documents/filename.txt`)

### Step 2: Embed in Workspace
```bash
POST /api/v1/workspace/{slug}/update-embeddings
```
Chunks the text and creates embeddings, making it available for RAG queries

---

## Quick Test (5 minutes)

Run this to test everything works:

```bash
cd /volume1/docker/greenfrog-rag
chmod +x test-anythingllm-api.sh
./test-anythingllm-api.sh --create-test-file
```

**Expected output:**
- Document uploaded successfully
- Document embedded successfully
- Test complete

Then check: http://localhost:3001 → workspace "greenfrog" → should see document in sidebar

---

## The Correct API Calls

### Using cURL (Direct HTTP)

**Step 1: Upload**
```bash
curl -X POST 'http://localhost:3001/api/v1/document/upload' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -F 'file=@/path/to/document.pdf'
```

Note the document location from response (e.g., `custom-documents/document.txt`)

**Step 2: Embed**
```bash
curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/update-embeddings' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json' \
  -d '{"adds": ["custom-documents/document.txt"]}'
```

### Using Python

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

### Using Node.js

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

## Critical Details

### Workspace Slug vs ID
- **Wrong:** `/api/v1/workspace/1/update-embeddings` (using ID)
- **Correct:** `/api/v1/workspace/greenfrog/update-embeddings` (using slug)

Your workspace: `greenfrog` (slug) = `1` (ID)

### Document Path Format
- Upload returns: `custom-documents/document.txt`
- Always `.txt` (not original extension like `.pdf`)
- Case-sensitive on Linux

### Your Configuration
- Instance: `http://localhost:3001`
- Workspace: `greenfrog`
- API Key: `sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA`

---

## Documentation & Tools

| What | Where | When |
|------|-------|------|
| Quick lookup | `QUICK_API_REFERENCE.md` | Need a fast answer |
| Complete research | `API_RESEARCH_SUMMARY.md` | Want full understanding |
| Detailed workflow | `ANYTHINGLLM_API_WORKFLOW.md` | Implementing in detail |
| Test script | `./test-anythingllm-api.sh` | Want to verify it works |
| Python client | `anythingllm_client.py` | Building Python integration |
| Node.js client | `anythingllm-client.js` | Building Node.js integration |
| cURL examples | `CURL_EXAMPLES.sh` | Need copy-paste commands |
| File index | `INDEX.md` | Want navigation guide |
| This file | `00_START_HERE.md` | Reading now |

---

## Troubleshooting

### "Documents not appearing in workspace"
- Forgot Step 2? Call the embed endpoint
- Check workspace slug (should be "greenfrog")
- Check document path (should be "custom-documents/name.txt")

### "404 on upload endpoint"
- Using wrong endpoint
- Right: `/api/v1/document/upload` (global)
- Wrong: `/api/v1/workspace/{slug}/upload` (this doesn't exist)

### "Document not found when embedding"
- Using wrong document path
- Use exact path from upload response
- Always ends with `.txt`

### "Embedder not configured"
- Go to AnythingLLM Settings
- Select an embedder (local or remote)
- Try embedding again

---

## Verification

After uploading and embedding:

1. **UI Check**
   - Open http://localhost:3001
   - Go to workspace "greenfrog"
   - Look for document in sidebar
   - Status should be "embedded"

2. **API Check**
   ```bash
   curl -X GET 'http://localhost:3001/api/v1/workspace/greenfrog' \
     -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA'
   ```
   Document should appear in response

3. **RAG Check**
   ```bash
   curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/chat' \
     -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
     -H 'Content-Type: application/json' \
     -d '{"message": "What is in the document?", "mode": "query"}'
   ```
   Should reference the document content

---

## Common Mistakes

```
WRONG:  /api/v1/workspace/1/upload                 ❌ (wrong endpoint)
RIGHT:  /api/v1/document/upload                    ✅

WRONG:  /api/v1/workspace/1/update-embeddings      ❌ (using ID)
RIGHT:  /api/v1/workspace/greenfrog/update-embeddings ✅

WRONG:  {"adds": ["document.pdf"]}                 ❌ (wrong path)
RIGHT:  {"adds": ["custom-documents/document.txt"]} ✅

WRONG:  Skipping the embed step                    ❌ (document stays uploaded)
RIGHT:  Always call both endpoints                 ✅
```

---

## Next Steps

1. **Try it now:**
   ```bash
   ./test-anythingllm-api.sh --create-test-file
   ```

2. **Read quick reference:**
   Open `QUICK_API_REFERENCE.md`

3. **Use in your code:**
   See Python or Node.js client examples above

4. **Need details?**
   Read `ANYTHINGLLM_API_WORKFLOW.md`

---

## Key Facts

- ✅ Two-step workflow is intentional design
- ✅ Upload and embed are separate endpoints
- ✅ Document path format is strict
- ✅ Workspace slug (not ID) required in API
- ✅ All operations are asynchronous
- ✅ Processing time depends on document size

---

## Support

- **Official Docs:** https://docs.anythingllm.com/
- **GitHub:** https://github.com/Mintplex-Labs/anything-llm
- **API Docs:** https://docs.useanything.com/features/api

---

## Summary

**Problem:** Documents not appearing in workspace

**Root Cause:** Missing two-step API workflow

**Solution:**
1. Upload: `POST /api/v1/document/upload`
2. Embed: `POST /api/v1/workspace/greenfrog/update-embeddings`

**Test:** Run `./test-anythingllm-api.sh --create-test-file`

**Learn More:** Read documentation files in this directory

---

**Status:** READY TO USE ✅

All workflows tested and verified from official AnythingLLM sources.
