"""
RAG Service - AnythingLLM Integration
Handles chat queries and document retrieval
"""

import httpx
import structlog
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = structlog.get_logger(__name__)


class RAGService:
    """
    AnythingLLM RAG Service
    Handles chat queries with retrieval-augmented generation
    """

    def __init__(
        self,
        base_url: str = "http://anythingllm:3001",
        api_key: Optional[str] = None
    ):
        """
        Initialize RAG service

        Args:
            base_url: AnythingLLM base URL
            api_key: AnythingLLM API key (if auth enabled)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=60.0)

        # Set up headers
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

        logger.info("rag_service_initialized", base_url=base_url)

    async def chat(
        self,
        message: str,
        workspace_slug: str = "greenfrog",
        mode: str = "chat",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send chat message to AnythingLLM workspace

        Args:
            message: User message
            workspace_slug: Workspace identifier
            mode: Chat mode ('chat' or 'query')
            temperature: LLM temperature (0-2)
            max_tokens: Maximum response tokens
            session_id: Session ID for context persistence

        Returns:
            Dict with response, sources, and metadata
        """
        logger.info("chat_request",
                   workspace=workspace_slug,
                   mode=mode,
                   message_length=len(message),
                   session_id=session_id)

        try:
            # Construct endpoint based on mode
            endpoint = f"{self.base_url}/api/v1/workspace/{workspace_slug}/{mode}"

            # Build request payload
            payload = {
                "message": message,
                "mode": mode
            }

            # Add optional parameters
            if session_id:
                payload["sessionId"] = session_id

            # Send request
            response = await self.client.post(
                endpoint,
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()

            data = response.json()

            logger.info("chat_success",
                       workspace=workspace_slug,
                       sources_count=len(data.get("sources", [])))

            return {
                "response": data.get("textResponse", ""),
                "sources": data.get("sources", []),
                "session_id": data.get("id", session_id or "default"),
                "model": data.get("model", "unknown"),
                "timestamp": datetime.utcnow()
            }

        except httpx.HTTPStatusError as e:
            logger.error("chat_http_error",
                        status_code=e.response.status_code,
                        error=str(e))
            raise Exception(f"AnythingLLM error: {e.response.status_code}")

        except Exception as e:
            logger.error("chat_error", error=str(e))
            raise Exception(f"Chat failed: {str(e)}")

    async def query(
        self,
        question: str,
        workspace_slug: str = "greenfrog",
        max_tokens: int = 1024
    ) -> Dict[str, Any]:
        """
        Query workspace with single question (no chat history)

        Args:
            question: User question
            workspace_slug: Workspace identifier
            max_tokens: Maximum response tokens

        Returns:
            Dict with response and sources
        """
        return await self.chat(
            message=question,
            workspace_slug=workspace_slug,
            mode="query",
            max_tokens=max_tokens
        )

    async def get_workspaces(self) -> List[Dict[str, Any]]:
        """
        Get list of available workspaces

        Returns:
            List of workspace metadata
        """
        logger.info("get_workspaces_request")

        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/workspaces",
                headers=self.headers
            )
            response.raise_for_status()

            data = response.json()
            workspaces = data.get("workspaces", [])

            logger.info("get_workspaces_success", count=len(workspaces))
            return workspaces

        except Exception as e:
            logger.error("get_workspaces_error", error=str(e))
            return []

    async def create_workspace(
        self,
        name: str,
        slug: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create new workspace

        Args:
            name: Workspace name
            slug: Workspace slug (auto-generated if not provided)

        Returns:
            Workspace metadata
        """
        logger.info("create_workspace_request", name=name, slug=slug)

        try:
            payload = {"name": name}
            if slug:
                payload["slug"] = slug

            response = await self.client.post(
                f"{self.base_url}/api/v1/workspace/new",
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()

            data = response.json()
            logger.info("create_workspace_success", workspace=data.get("workspace"))
            return data.get("workspace", {})

        except Exception as e:
            logger.error("create_workspace_error", error=str(e))
            raise Exception(f"Failed to create workspace: {str(e)}")

    async def upload_document(
        self,
        workspace_slug: str,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload document to workspace

        Args:
            workspace_slug: Target workspace
            file_path: Path to document file
            metadata: Optional document metadata

        Returns:
            Upload result metadata
        """
        logger.info("upload_document_request",
                   workspace=workspace_slug,
                   file_path=file_path)

        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}

                response = await self.client.post(
                    f"{self.base_url}/api/v1/workspace/{workspace_slug}/upload",
                    files=files,
                    headers={k: v for k, v in self.headers.items() if k != "Content-Type"}
                )
                response.raise_for_status()

                data = response.json()
                logger.info("upload_document_success", workspace=workspace_slug)
                return data

        except Exception as e:
            logger.error("upload_document_error", error=str(e))
            raise Exception(f"Failed to upload document: {str(e)}")

    async def get_workspace_stats(
        self,
        workspace_slug: str
    ) -> Dict[str, Any]:
        """
        Get workspace statistics

        Args:
            workspace_slug: Workspace identifier

        Returns:
            Workspace statistics
        """
        logger.info("get_workspace_stats", workspace=workspace_slug)

        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/workspace/{workspace_slug}",
                headers=self.headers
            )
            response.raise_for_status()

            data = response.json()
            logger.info("workspace_stats_success", workspace=workspace_slug)
            return data.get("workspace", {})

        except Exception as e:
            logger.error("workspace_stats_error", error=str(e))
            return {}

    async def health_check(self) -> bool:
        """
        Check if AnythingLLM is healthy

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/ping",
                timeout=5.0
            )
            return response.status_code == 200

        except Exception as e:
            logger.warning("anythingllm_health_check_failed", error=str(e))
            return False

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
        logger.info("rag_service_closed")


# Global RAG service instance
_rag_instance: Optional[RAGService] = None


def get_rag_service(
    base_url: str = "http://anythingllm:3001",
    api_key: Optional[str] = None
) -> RAGService:
    """
    Get or create RAG service instance

    Args:
        base_url: AnythingLLM base URL
        api_key: AnythingLLM API key

    Returns:
        RAGService instance
    """
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGService(base_url=base_url, api_key=api_key)
    return _rag_instance
