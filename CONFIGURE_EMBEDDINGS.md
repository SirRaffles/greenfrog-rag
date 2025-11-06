# Configure AnythingLLM Embeddings - CORRECTED INSTRUCTIONS

## Issue Identified
The workspace settings don't show embedding provider configuration because **embeddings must be configured at the SYSTEM level first**, not at the workspace level.

## Correct Configuration Steps

### 1. Access System Settings (Not Workspace Settings)

**Location:** Look for the **wrench/gear icon** in the **bottom-left sidebar** (NOT the workspace settings gear)

Or access directly:
```
http://192.168.50.171:3001/settings
```

### 2. Navigate to Embedding Configuration

In the left sidebar, you should see:
- General
- **LLM Preference** 
- **Embedding Preference** ← Click this
- Vector Database
- etc.

### 3. Configure Embedding Provider

**In "Embedding Preference" section:**

1. **Provider:** Select **"Ollama"** from dropdown
2. **Ollama Base URL:** Enter `http://host.docker.internal:11434`
3. **Embedding Model:** Enter `nomic-embed-text:latest`
4. Click **"Save Embedding Settings"**

### 4. Configure LLM Provider (System Level)

**In "LLM Preference" section:**

1. **Provider:** Select **"Ollama"** from dropdown
2. **Ollama Base URL:** Enter `http://host.docker.internal:11434`
3. **Chat Model:** Select or enter `llama3.1:8b`
4. **Token Context Window:** `128000` (default for llama3.1)
5. Click **"Save LLM Settings"**

### 5. Return to Workspace and Test

After configuring system settings:
1. Go back to "GreenFrog Sustainability" workspace
2. Try a chat query: "What is the Matcha Initiative?"
3. Should now return document-based answers

## Visual Guide

```
┌─────────────────────────────────────────┐
│  AnythingLLM Sidebar                    │
├─────────────────────────────────────────┤
│  🏠 Home                                │
│  💬 GreenFrog Sustainability (workspace)│
│  📁 Documents                           │
│  ⚙️  Settings ← CLICK THIS (system)    │
│     ├─ General                          │
│     ├─ LLM Preference ← Configure       │
│     ├─ Embedding Preference ← Configure │
│     ├─ Vector Database                  │
│     └─ ...                              │
└─────────────────────────────────────────┘
```

## Verification

After configuration, check:

1. **Vector Count should increase**
   - Go to workspace → Vector Database section
   - Should show "Vector Count: 460" (or similar)

2. **Test RAG Query**
   - Send message: "What is the Matcha Initiative?"
   - Should return answer based on embedded documents

## If Vector Count is Still 0

The documents may need to be re-embedded:

```bash
# Re-run content loader
cd /volume1/docker/greenfrog-rag
python3 scripts/load_content.py
```

## Alternative: Via API

If UI configuration doesn't work, you can configure via API:

```bash
# Set embedding provider
curl -X POST http://192.168.50.171:3001/api/system/embedding-preference \
  -H "Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "config": {
      "baseUrl": "http://host.docker.internal:11434",
      "model": "nomic-embed-text:latest"
    }
  }'

# Set LLM provider
curl -X POST http://192.168.50.171:3001/api/system/llm-preference \
  -H "Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "config": {
      "baseUrl": "http://host.docker.internal:11434",
      "model": "llama3.1:8b",
      "maxTokens": 128000
    }
  }'
```

## Summary

**Key Point:** Embedding provider is configured at **SYSTEM SETTINGS** level, not workspace level.

**Steps:**
1. Click Settings (wrench icon) in bottom-left sidebar
2. Click "Embedding Preference"
3. Set Ollama + nomic-embed-text:latest
4. Click "LLM Preference"
5. Set Ollama + llama3.1:8b
6. Save both
7. Test in workspace chat

**Expected Result:** Vector Count: 460, RAG queries work
