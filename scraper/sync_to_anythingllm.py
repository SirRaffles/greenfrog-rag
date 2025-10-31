#!/usr/bin/env python3
"""
Sync scraped content to AnythingLLM for RAG processing
Monitors the scraped content directory and uploads new/updated documents
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

import httpx
from pydantic import BaseModel

# Configuration
ANYTHINGLLM_URL = os.getenv("ANYTHINGLLM_URL", "http://anythingllm:3001")
ANYTHINGLLM_API_KEY = os.getenv("ANYTHINGLLM_API_KEY", "")
WORKSPACE_SLUG = os.getenv("WORKSPACE_SLUG", "greenfrog-matcha")
INPUT_DIR = Path(os.getenv("INPUT_DIR", "/data/matchainitiative"))
STATE_FILE = Path(os.getenv("SYNC_STATE_FILE", "/data/state/sync_state.json"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/logs/sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DocumentState(BaseModel):
    """State tracking for a single document"""
    file_path: str
    content_hash: str
    last_synced: datetime
    anythingllm_doc_id: Optional[str] = None
    status: str  # "synced", "failed", "pending"


class SyncState(BaseModel):
    """Overall sync state"""
    last_run: Optional[datetime] = None
    documents: Dict[str, DocumentState] = {}
    total_documents: int = 0
    synced_documents: int = 0
    failed_documents: int = 0
    new_documents: int = 0
    updated_documents: int = 0


class AnythingLLMClient:
    """Client for AnythingLLM API"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            timeout=60.0,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            } if api_key else {"Content-Type": "application/json"}
        )

    async def health_check(self) -> bool:
        """Check if AnythingLLM is accessible"""
        try:
            response = await self.client.get(f"{self.base_url}/api/ping")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def get_workspaces(self) -> List[Dict]:
        """Get list of workspaces"""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/workspaces")
            response.raise_for_status()
            return response.json().get("workspaces", [])
        except Exception as e:
            logger.error(f"Failed to get workspaces: {e}")
            return []

    async def get_or_create_workspace(self, slug: str, name: str = None) -> Optional[Dict]:
        """Get existing workspace or create new one"""
        try:
            # Check if workspace exists
            workspaces = await self.get_workspaces()
            for workspace in workspaces:
                if workspace.get("slug") == slug:
                    logger.info(f"Workspace '{slug}' already exists")
                    return workspace

            # Create new workspace
            logger.info(f"Creating workspace '{slug}'")
            response = await self.client.post(
                f"{self.base_url}/api/v1/workspace/new",
                json={
                    "name": name or slug,
                    "slug": slug
                }
            )
            response.raise_for_status()
            result = response.json()

            if result.get("workspace"):
                logger.info(f"  ✓ Workspace created: {result['workspace'].get('id')}")
                return result["workspace"]
            else:
                logger.error(f"Failed to create workspace: {result}")
                return None

        except Exception as e:
            logger.error(f"Error getting/creating workspace: {e}")
            return None

    async def upload_document(self, workspace_slug: str, document_data: Dict) -> Optional[str]:
        """Upload a document to workspace"""
        try:
            # Convert JSON content to text format suitable for RAG
            content_text = self._format_document_content(document_data)

            # Upload document
            response = await self.client.post(
                f"{self.base_url}/api/v1/workspace/{workspace_slug}/upload",
                json={
                    "textContent": content_text,
                    "metadata": {
                        "source": "matcha_scraper",
                        "url": document_data.get("url", ""),
                        "title": document_data.get("title", ""),
                        "scraped_at": document_data.get("scraped_at", "")
                    }
                }
            )
            response.raise_for_status()
            result = response.json()

            if result.get("success"):
                doc_id = result.get("document", {}).get("id")
                logger.info(f"  ✓ Document uploaded: {doc_id}")
                return doc_id
            else:
                logger.error(f"  ✗ Upload failed: {result.get('error', 'Unknown error')}")
                return None

        except Exception as e:
            logger.error(f"  ✗ Error uploading document: {e}")
            return None

    async def update_document(self, workspace_slug: str, doc_id: str, document_data: Dict) -> bool:
        """Update an existing document"""
        try:
            # For now, delete and re-upload (AnythingLLM doesn't have direct update)
            # In production, you might want to check if this is the best approach
            content_text = self._format_document_content(document_data)

            response = await self.client.put(
                f"{self.base_url}/api/v1/workspace/{workspace_slug}/document/{doc_id}",
                json={
                    "textContent": content_text,
                    "metadata": {
                        "source": "matcha_scraper",
                        "url": document_data.get("url", ""),
                        "title": document_data.get("title", ""),
                        "scraped_at": document_data.get("scraped_at", ""),
                        "updated_at": datetime.now().isoformat()
                    }
                }
            )
            response.raise_for_status()
            result = response.json()

            if result.get("success"):
                logger.info(f"  ✓ Document updated: {doc_id}")
                return True
            else:
                logger.error(f"  ✗ Update failed: {result.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            logger.error(f"  ✗ Error updating document: {e}")
            return False

    def _format_document_content(self, document_data: Dict) -> str:
        """Format document content for RAG ingestion"""
        parts = []

        # Title
        if document_data.get("title"):
            parts.append(f"# {document_data['title']}\n")

        # URL
        if document_data.get("url"):
            parts.append(f"**Source URL:** {document_data['url']}\n")

        # Description
        if document_data.get("description"):
            parts.append(f"**Description:** {document_data['description']}\n")

        # Metadata
        if document_data.get("metadata"):
            metadata = document_data["metadata"]
            if metadata:
                parts.append("\n**Metadata:**")
                for key, value in metadata.items():
                    parts.append(f"- {key}: {value}")
                parts.append("")

        # Main content
        if document_data.get("text"):
            parts.append("\n---\n")
            parts.append(document_data["text"])

        return "\n".join(parts)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class ContentSyncer:
    """Syncs scraped content to AnythingLLM"""

    def __init__(self):
        self.input_dir = INPUT_DIR
        self.state_file = STATE_FILE
        self.state = self._load_state()
        self.anythingllm = AnythingLLMClient(ANYTHINGLLM_URL, ANYTHINGLLM_API_KEY)

        # Create state directory
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> SyncState:
        """Load sync state from disk"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                return SyncState(**data)
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
                return SyncState()
        return SyncState()

    def _save_state(self):
        """Save sync state to disk"""
        try:
            with open(self.state_file, 'w') as f:
                f.write(self.state.model_dump_json(indent=2))
            logger.info(f"State saved to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute hash of file content"""
        import hashlib
        return hashlib.sha256(file_path.read_bytes()).hexdigest()

    def _find_documents(self) -> List[Path]:
        """Find all JSON documents in input directory"""
        if not self.input_dir.exists():
            logger.warning(f"Input directory does not exist: {self.input_dir}")
            return []

        return list(self.input_dir.rglob("*.json"))

    async def _sync_document(self, file_path: Path, workspace_slug: str) -> Optional[DocumentState]:
        """Sync a single document"""
        try:
            relative_path = str(file_path.relative_to(self.input_dir))
            logger.info(f"Syncing: {relative_path}")

            # Read document
            with open(file_path, 'r') as f:
                document_data = json.load(f)

            # Compute content hash
            content_hash = self._compute_file_hash(file_path)

            # Check if document has changed
            existing_state = self.state.documents.get(relative_path)
            if existing_state and existing_state.content_hash == content_hash:
                logger.info(f"  → No changes detected, skipping")
                return DocumentState(
                    file_path=relative_path,
                    content_hash=content_hash,
                    last_synced=datetime.now(),
                    anythingllm_doc_id=existing_state.anythingllm_doc_id,
                    status="synced"
                )

            # Upload or update document
            if existing_state and existing_state.anythingllm_doc_id:
                # Update existing document
                success = await self.anythingllm.update_document(
                    workspace_slug,
                    existing_state.anythingllm_doc_id,
                    document_data
                )
                doc_id = existing_state.anythingllm_doc_id if success else None
                status = "synced" if success else "failed"
            else:
                # Upload new document
                doc_id = await self.anythingllm.upload_document(workspace_slug, document_data)
                status = "synced" if doc_id else "failed"

            return DocumentState(
                file_path=relative_path,
                content_hash=content_hash,
                last_synced=datetime.now(),
                anythingllm_doc_id=doc_id,
                status=status
            )

        except Exception as e:
            logger.error(f"  ✗ Error syncing {file_path}: {e}")
            return DocumentState(
                file_path=str(file_path.relative_to(self.input_dir)),
                content_hash="",
                last_synced=datetime.now(),
                status="failed"
            )

    async def run(self):
        """Main sync execution"""
        logger.info("=" * 80)
        logger.info("GreenFrog Content Syncer to AnythingLLM")
        logger.info("=" * 80)
        logger.info(f"AnythingLLM URL: {ANYTHINGLLM_URL}")
        logger.info(f"Workspace: {WORKSPACE_SLUG}")
        logger.info(f"Input directory: {self.input_dir}")
        logger.info(f"Batch size: {BATCH_SIZE}")
        logger.info("")

        start_time = time.time()

        # Health check
        logger.info("Checking AnythingLLM connection...")
        if not await self.anythingllm.health_check():
            logger.error("AnythingLLM is not accessible. Aborting sync.")
            return

        logger.info("  ✓ AnythingLLM is accessible")

        # Get or create workspace
        logger.info(f"Ensuring workspace '{WORKSPACE_SLUG}' exists...")
        workspace = await self.anythingllm.get_or_create_workspace(
            WORKSPACE_SLUG,
            "GreenFrog Matcha Initiative"
        )

        if not workspace:
            logger.error("Failed to get/create workspace. Aborting sync.")
            return

        logger.info(f"  ✓ Using workspace: {workspace.get('id')}")
        logger.info("")

        # Find all documents
        documents = self._find_documents()
        logger.info(f"Found {len(documents)} documents to sync")

        if not documents:
            logger.warning("No documents found. Exiting.")
            return

        # Process documents in batches
        for i in range(0, len(documents), BATCH_SIZE):
            batch = documents[i:i + BATCH_SIZE]
            logger.info(f"\nProcessing batch {i // BATCH_SIZE + 1} ({len(batch)} documents)...")

            tasks = [self._sync_document(doc, WORKSPACE_SLUG) for doc in batch]
            results = await asyncio.gather(*tasks)

            # Update state
            for result in results:
                if result:
                    old_state = self.state.documents.get(result.file_path)
                    self.state.documents[result.file_path] = result

                    if result.status == "synced":
                        self.state.synced_documents += 1
                        if not old_state:
                            self.state.new_documents += 1
                        elif old_state.content_hash != result.content_hash:
                            self.state.updated_documents += 1
                    elif result.status == "failed":
                        self.state.failed_documents += 1

            # Small delay between batches
            if i + BATCH_SIZE < len(documents):
                await asyncio.sleep(2)

        # Update final state
        self.state.total_documents = len(documents)
        self.state.last_run = datetime.now()
        self._save_state()

        # Close client
        await self.anythingllm.close()

        # Print summary
        elapsed_time = time.time() - start_time
        logger.info("")
        logger.info("=" * 80)
        logger.info("SYNC COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total documents processed: {self.state.total_documents}")
        logger.info(f"  → Synced: {self.state.synced_documents}")
        logger.info(f"  → Failed: {self.state.failed_documents}")
        logger.info(f"  → New documents: {self.state.new_documents}")
        logger.info(f"  → Updated documents: {self.state.updated_documents}")
        logger.info(f"Elapsed time: {elapsed_time:.2f}s")
        logger.info("=" * 80)


async def main():
    """Main entry point"""
    syncer = ContentSyncer()
    await syncer.run()


if __name__ == "__main__":
    asyncio.run(main())
