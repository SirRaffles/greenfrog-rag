# AnythingLLM API - Implementation Checklist

## Pre-Implementation (Before You Start)

- [ ] AnythingLLM is running and accessible at `http://localhost:3001`
- [ ] API key is valid: `sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA`
- [ ] Workspace "greenfrog" exists
- [ ] Have documents ready to upload
- [ ] Read `00_START_HERE.md` (5 min)

## Test Setup (Verify Everything Works)

- [ ] Download test script: `test-anythingllm-api.sh`
- [ ] Make executable: `chmod +x test-anythingllm-api.sh`
- [ ] Run test with file creation:
  ```bash
  ./test-anythingllm-api.sh --create-test-file
  ```
- [ ] Test output shows "SUCCESS" messages
- [ ] No errors in output

## Verification After Test

- [ ] Open http://localhost:3001 in browser
- [ ] Navigate to workspace "greenfrog"
- [ ] Check sidebar for test document
- [ ] Document status shows "embedded"
- [ ] Document appears in workspace documents list

## Understanding the Workflow (Read & Understand)

- [ ] Understand Step 1: Upload converts file to text
- [ ] Understand Step 2: Embed chunks text and creates vectors
- [ ] Understand workspace slug vs ID
  - [ ] Slug: "greenfrog" (used in API)
  - [ ] ID: "1" (internal database)
- [ ] Understand document path format: `custom-documents/filename.txt`
- [ ] Understand both steps are required
- [ ] Read `QUICK_API_REFERENCE.md` for quick lookup

## API Implementation - Option A: Using Python

### Setup
- [ ] Python 3.6+ installed
- [ ] `requests` module available (pip install requests)
- [ ] Have `anythingllm_client.py` in your project

### Simple Implementation
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

assert embed_result.success, f"Failed: {embed_result.message}"
print(f"Document embedded: {upload_result.location}")
```

### Implementation Checklist
- [ ] Import AnythingLLMClient from anythingllm_client
- [ ] Create client with correct URL and API key
- [ ] Call uploadAndEmbed() with file path and workspace
- [ ] Check result.success is True
- [ ] Handle errors appropriately
- [ ] Test with multiple file formats (PDF, DOCX, TXT, etc.)
- [ ] Test with multiple documents
- [ ] Verify documents appear in workspace

### Batch Processing
- [ ] For multiple files, use upload_multiple()
- [ ] Call upload_multiple() with list of file paths
- [ ] Handle partial failures (some files may fail)
- [ ] Verify all documents embedded successfully

### Production Readiness
- [ ] Add error handling for network failures
- [ ] Add logging for debugging
- [ ] Add retry logic for failed operations
- [ ] Add timeout handling
- [ ] Add validation for file paths
- [ ] Add checks for document embedding status
- [ ] Test with large documents
- [ ] Test with slow/unreliable networks

## API Implementation - Option B: Using Node.js

### Setup
- [ ] Node.js 14+ installed
- [ ] `form-data` module available (npm install form-data)
- [ ] Have `anythingllm-client.js` in your project

### Simple Implementation
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

if (result.success) {
  console.log('Document embedded:', result.upload.location);
} else {
  console.error('Failed:', result.error);
}
```

### Implementation Checklist
- [ ] Require/import AnythingLLMClient
- [ ] Create client with correct URL and API key
- [ ] Call uploadAndEmbed() with file path and workspace
- [ ] Check result.success is true
- [ ] Handle errors with proper error messages
- [ ] Test with multiple file formats
- [ ] Test with multiple documents
- [ ] Verify documents appear in workspace
- [ ] Use proper async/await patterns
- [ ] Add proper error handling with try/catch

### Batch Processing
- [ ] For multiple files, use uploadMultiple()
- [ ] Call uploadMultiple() with array of file paths
- [ ] Track which files succeeded/failed
- [ ] Retry failures as needed
- [ ] Verify all documents embedded

### Production Readiness
- [ ] Add comprehensive error handling
- [ ] Add structured logging
- [ ] Add timeout configurations
- [ ] Add retry logic with exponential backoff
- [ ] Add file validation
- [ ] Add status verification after embedding
- [ ] Test with large files
- [ ] Test connection timeouts and failures

## API Implementation - Option C: Using cURL/Bash

### Setup
- [ ] curl installed and working
- [ ] Have access to command line
- [ ] Can copy/paste commands

### Simple Implementation
```bash
# Step 1: Upload
RESPONSE=$(curl -s -X POST 'http://localhost:3001/api/v1/document/upload' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -F 'file=@/path/to/document.pdf')

DOC_LOCATION=$(echo "$RESPONSE" | grep -o '"location":"[^"]*"' | cut -d'"' -f4)

# Step 2: Embed
curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/update-embeddings' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json' \
  -d "{\"adds\": [\"$DOC_LOCATION\"]}"
```

### Implementation Checklist
- [ ] Copy upload command from CURL_EXAMPLES.sh
- [ ] Replace file path with your document
- [ ] Extract location from response
- [ ] Copy embed command
- [ ] Replace location in embed command
- [ ] Execute both commands
- [ ] Check for success in responses
- [ ] Verify document appears in workspace

### Batch Processing
- [ ] Create loop for multiple files
- [ ] Upload each file
- [ ] Collect all locations
- [ ] Call embed once with all locations
- [ ] Or embed each individually

### Scripting Best Practices
- [ ] Use proper error handling
- [ ] Check curl exit codes
- [ ] Parse JSON responses correctly
- [ ] Use jq for JSON parsing if available
- [ ] Add proper logging
- [ ] Handle special characters in filenames

## Document Verification

### After Each Upload
- [ ] Check HTTP status code (200 or 201)
- [ ] Parse response JSON
- [ ] Verify "document" object exists
- [ ] Verify "location" field is present
- [ ] Store location for embed step

### After Each Embed
- [ ] Check HTTP status code (200 or 201)
- [ ] Verify success field in response
- [ ] Check message field
- [ ] Wait 1-2 seconds
- [ ] Verify document appears in workspace

### Verify in UI
- [ ] Open http://localhost:3001
- [ ] Go to correct workspace ("greenfrog")
- [ ] Look in left sidebar
- [ ] Document should be listed
- [ ] Status should show "embedded"
- [ ] Click document to see details

### Verify via API
```bash
curl -X GET 'http://localhost:3001/api/v1/workspace/greenfrog' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA'
```
- [ ] Response includes "documents" array
- [ ] Your document appears in the array
- [ ] Status shows "embedded"

### Verify with RAG Query
```bash
curl -X POST 'http://localhost:3001/api/v1/workspace/greenfrog/chat' \
  -H 'Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA' \
  -H 'Content-Type: application/json' \
  -d '{"message": "What is in the document?", "mode": "query"}'
```
- [ ] Response from LLM
- [ ] References document content
- [ ] Indicates document is embedded and available

## Troubleshooting Checklist

### If Documents Don't Appear

#### Check Prerequisites
- [ ] AnythingLLM is running: `curl http://localhost:3001`
- [ ] Workspace exists: Check UI
- [ ] API key is correct
- [ ] Using workspace slug (not ID)

#### Check Upload Step
- [ ] Upload endpoint returns 200/201
- [ ] Response includes "document" object
- [ ] "location" field contains path
- [ ] Path starts with "custom-documents/"

#### Check Embed Step
- [ ] Embed endpoint returns 200/201
- [ ] Document path matches upload response exactly
- [ ] No typos in workspace slug
- [ ] Using workspace slug not ID

#### Wait for Processing
- [ ] Wait 2-5 seconds after embed
- [ ] Check AnythingLLM logs: `docker logs anythingllm`
- [ ] Look for embedding-related messages
- [ ] Check for error messages

#### Check Embedder Configuration
- [ ] Open AnythingLLM Settings
- [ ] Go to Embedder section
- [ ] Embedder is selected
- [ ] Not showing "not configured" error
- [ ] Embedding model is downloaded

### If Getting 404 Errors

#### On Upload
- [ ] Using correct endpoint: `/api/v1/document/upload`
- [ ] Not using workspace-specific endpoint
- [ ] Endpoint path has no typos
- [ ] Full URL is `http://localhost:3001/api/v1/document/upload`

#### On Embed
- [ ] Using correct endpoint: `/api/v1/workspace/{slug}/update-embeddings`
- [ ] Workspace slug is correct ("greenfrog")
- [ ] Not using workspace ID (1)
- [ ] Full URL is `http://localhost:3001/api/v1/workspace/greenfrog/update-embeddings`

### If Getting 401 Errors

- [ ] API key is present in Authorization header
- [ ] Bearer token format: `Bearer {API_KEY}`
- [ ] API key is not expired
- [ ] No typos in API key
- [ ] Your key: `sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA`

### If Embedding Fails

- [ ] Check AnythingLLM logs for errors
- [ ] Verify embedder is configured in Settings
- [ ] Check if embedder download is stuck
- [ ] Look for memory/CPU issues
- [ ] Check network connectivity
- [ ] Try smaller document first

## Performance Optimization

### For Many Documents
- [ ] Use batch embedding (all at once vs one by one)
- [ ] Monitor memory usage during embedding
- [ ] Implement retry logic for failed embeds
- [ ] Consider scheduled uploads (not all at once)
- [ ] Monitor AnythingLLM CPU usage

### For Large Documents
- [ ] Upload large files individually first
- [ ] Monitor embedding progress in logs
- [ ] Increase timeout values
- [ ] Consider breaking into smaller files
- [ ] Check vector DB disk space

### For Slow Networks
- [ ] Increase timeout values in client
- [ ] Implement exponential backoff retry
- [ ] Upload files during off-peak hours
- [ ] Use compression if available
- [ ] Split large files if possible

## Production Deployment

- [ ] Error handling comprehensive
- [ ] Logging configured
- [ ] Retry logic implemented
- [ ] Timeouts appropriate
- [ ] Input validation in place
- [ ] Error messages informative
- [ ] Status checks automated
- [ ] Monitoring configured
- [ ] Backup system for documents
- [ ] Testing complete

## Documentation & Maintenance

- [ ] Code well-commented
- [ ] API configuration documented
- [ ] Error handling documented
- [ ] Retry logic explained
- [ ] Troubleshooting guide available
- [ ] Runbook created
- [ ] Team trained on API usage
- [ ] Support procedures defined

## Final Validation

- [ ] All test documents embedded successfully
- [ ] RAG queries return correct results
- [ ] Error handling works as expected
- [ ] Performance meets requirements
- [ ] Logging provides useful information
- [ ] Team can troubleshoot issues
- [ ] Documentation is current
- [ ] Ready for production use

---

## Checklist Summary

| Phase | Items | Completed |
|-------|-------|-----------|
| Pre-Implementation | 5 | [ ] |
| Test Setup | 4 | [ ] |
| Verification | 3 | [ ] |
| Understanding | 8 | [ ] |
| Implementation | Varies | [ ] |
| Document Verification | 12 | [ ] |
| Troubleshooting | 20+ | As needed |
| Performance | 6 | [ ] |
| Production | 8 | [ ] |
| Documentation | 5 | [ ] |
| Final Validation | 8 | [ ] |

---

**Total estimated time:** 2-4 hours from start to production-ready

**Quick test only:** 15 minutes with `./test-anythingllm-api.sh`
