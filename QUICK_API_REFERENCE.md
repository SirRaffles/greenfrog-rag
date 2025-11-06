# AnythingLLM API - Quick Reference

## Your Configuration
- Instance: `http://localhost:3001`
- Workspace: `greenfrog`
- API Key: `sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA`

## The Two-Step Workflow

### 1. Upload Document
```bash
curl -X POST 'http://localhost:3001/api/v1/document/upload' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -F 'file=@/path/to/file.pdf'
```

**Result:** File stored as `custom-documents/file.txt`

### 2. Embed in Workspace
```bash
curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/update-embeddings' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json' \
  -d '{"adds": ["custom-documents/file.txt"]}'
```

**Result:** Document embedded in workspace, ready for RAG queries

---

## Why Documents Don't Appear

| Issue | Cause | Solution |
|-------|-------|----------|
| Empty workspace | Step 2 skipped | Call `/update-embeddings` endpoint |
| "Not found" error | Wrong filename | Use exact name from upload response |
| Files uploaded before | Embed old files | Use `custom-documents/filename.txt` |
| Upload returns 404 | Wrong endpoint | Use `/api/v1/document/upload` (global) |
| Embed returns 404 | Wrong workspace | Verify workspace slug is correct |

---

## Common Endpoints

| Action | Endpoint | Method |
|--------|----------|--------|
| Upload file | `/api/v1/document/upload` | POST |
| Embed in workspace | `/api/v1/workspace/{slug}/update-embeddings` | POST |
| Remove from workspace | `/api/v1/workspace/{slug}/update-embeddings` | POST (with "removes") |
| Chat with workspace | `/api/v1/workspace/{slug}/chat` | POST |
| Workspace info | `/api/v1/workspace/{slug}` | GET |

---

## Key Points to Remember

1. **Upload ≠ Embed**
   - Upload creates text file in system storage
   - Embed chunks it and creates vectors in vector DB

2. **Document Path Pattern**
   - After upload: `custom-documents/{name}.txt`
   - Original extension doesn't matter (PDF→TXT)
   - Use this exact path in embed endpoint

3. **Workspace Slug**
   - Use workspace slug ("greenfrog"), not ID (1)
   - Found in workspace URL and settings

4. **Processing Time**
   - Upload: instant
   - Embedding: depends on document size (seconds to minutes)

---

## Test the Complete Workflow

```bash
# Make executable
chmod +x test-anythingllm-api.sh

# Run with test file creation
./test-anythingllm-api.sh --create-test-file

# Or upload your own file
./test-anythingllm-api.sh --file /path/to/document.pdf

# Verbose output for debugging
./test-anythingllm-api.sh --create-test-file --verbose
```

---

## Troubleshooting Checklist

- [ ] API key is correct: `sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA`
- [ ] AnythingLLM running: `curl http://localhost:3001`
- [ ] Workspace exists: Check UI or list workspaces
- [ ] Using workspace slug not ID: "greenfrog" not "1"
- [ ] Upload endpoint returns success
- [ ] Using correct document path: `custom-documents/name.txt`
- [ ] Waiting for embedding to complete
- [ ] Checking AnythingLLM logs: `docker logs anythingllm`

---

## Full Documentation

See: `/volume1/docker/greenfrog-rag/ANYTHINGLLM_API_WORKFLOW.md`

## Test Script

See: `/volume1/docker/greenfrog-rag/test-anythingllm-api.sh`
