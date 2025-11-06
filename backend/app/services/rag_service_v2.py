"""
RAG Service V2 - Core Orchestration Layer

This service orchestrates the entire RAG pipeline, integrating:
- Semantic caching (Redis)
- Hybrid retrieval (BM25 + Semantic)
- Reranking (score-based)
- LLM generation (Ollama)
- SSE streaming

Architecture:
1. Cache check (semantic similarity-based)
2. If miss: Retrieve documents (hybrid search)
3. Rerank documents (if enabled)
4. Build context from top-k documents
5. Generate response (streaming or non-streaming)
6. Cache response for future queries
7. Return response with rich metadata
"""

import time
from typing import Dict, Any, List, Optional, Union, AsyncIterator
from datetime import datetime
import structlog

from app.services.cache_service import CacheService
from app.services.ollama_service import OllamaService
from app.services.retrieval_service import RetrievalService
from app.services.rerank_service import RerankService
from app.services.stream_service import StreamService

logger = structlog.get_logger(__name__)


class RAGServiceV2:
    """
    Production-ready RAG orchestration service.

    Features:
    - Cache-first architecture with semantic similarity
    - Hybrid retrieval (BM25 + semantic search)
    - Optional reranking for quality improvement
    - Streaming and non-streaming generation
    - Rich metadata and timing information
    - Graceful error handling and fallbacks
    - Context window management

    Pipeline:
    1. Semantic cache lookup
    2. Document retrieval (hybrid search)
    3. Document reranking (optional)
    4. Context construction
    5. LLM generation
    6. Response caching
    """

    # Context window limits for common models
    CONTEXT_LIMITS = {
        "phi3:mini": 4096,
        "llama3.2:3b": 8192,
        "nomic-embed-text:latest": 8192,
    }

    # Default RAG prompt template
    DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant. Use the provided context to answer questions accurately.
If the context doesn't contain enough information, say so clearly.
Always cite which source(s) you used in your answer."""

    DEFAULT_PROMPT_TEMPLATE = """Context:
{context}

Question: {question}

Answer based on the context provided above:"""

    def __init__(
        self,
        cache_service: CacheService,
        ollama_service: OllamaService,
        retrieval_service: RetrievalService,
        rerank_service: RerankService,
        stream_service: StreamService,
        model: str = "phi3:mini",
        use_cache: bool = True,
        use_rerank: bool = True,
        system_prompt: Optional[str] = None,
        prompt_template: Optional[str] = None,
    ):
        """
        Initialize RAG service V2.

        Args:
            cache_service: CacheService instance for semantic caching
            ollama_service: OllamaService instance for LLM generation
            retrieval_service: RetrievalService instance for hybrid search
            rerank_service: RerankService instance for result reranking
            stream_service: StreamService instance for SSE streaming
            model: Default LLM model to use
            use_cache: Enable semantic caching
            use_rerank: Enable document reranking
            system_prompt: Custom system prompt (default: DEFAULT_SYSTEM_PROMPT)
            prompt_template: Custom prompt template (default: DEFAULT_PROMPT_TEMPLATE)
        """
        self.cache_service = cache_service
        self.ollama_service = ollama_service
        self.retrieval_service = retrieval_service
        self.rerank_service = rerank_service
        self.stream_service = stream_service

        self.model = model
        self.use_cache = use_cache
        self.use_rerank = use_rerank

        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.prompt_template = prompt_template or self.DEFAULT_PROMPT_TEMPLATE

        # Get context limit for model
        self.context_limit = self.CONTEXT_LIMITS.get(model, 4096)

        logger.info(
            "rag_service_v2_init",
            model=model,
            use_cache=use_cache,
            use_rerank=use_rerank,
            context_limit=self.context_limit,
        )

    async def query(
        self,
        question: str,
        workspace: str = "greenfrog",
        k: int = 5,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        min_score: float = 0.0,
        model: Optional[str] = None,
    ) -> Union[Dict[str, Any], AsyncIterator[str]]:
        """
        Main RAG query method - orchestrates entire pipeline.

        Pipeline:
        1. Check semantic cache (if enabled)
        2. If cache miss:
           a. Retrieve relevant documents (hybrid search)
           b. Rerank results (if enabled)
           c. Build context from top k documents
           d. Generate prompt with context
           e. Call LLM (stream or non-stream)
           f. Cache response (if enabled)
        3. Return response with metadata

        Args:
            question: User question
            workspace: Workspace/collection identifier
            k: Number of documents to retrieve
            stream: Enable SSE streaming
            temperature: LLM sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            min_score: Minimum retrieval score threshold
            model: Override default model

        Returns:
            If stream=False: Response dict with answer, sources, and metadata
            If stream=True: AsyncIterator yielding SSE events

        Raises:
            ValueError: If question is empty
            Exception: If pipeline fails
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")

        model = model or self.model

        # Start timing
        start_time = time.time()

        logger.info(
            "rag_query_start",
            question_length=len(question),
            workspace=workspace,
            k=k,
            stream=stream,
            model=model,
        )

        try:
            # Step 1: Check cache (if enabled)
            cached_response = None
            cache_hit = False

            if self.use_cache:
                cache_start = time.time()
                cached_response = await self.cache_service.get(
                    query=question,
                    workspace=workspace,
                    use_semantic=True,
                )
                cache_time_ms = (time.time() - cache_start) * 1000

                if cached_response:
                    cache_hit = True
                    logger.info(
                        "rag_cache_hit",
                        cache_time_ms=round(cache_time_ms, 2),
                        workspace=workspace,
                    )

                    # Return cached response (with updated timestamp)
                    cached_response["metadata"]["cached"] = True
                    cached_response["metadata"]["cache_time_ms"] = round(cache_time_ms, 2)
                    cached_response["timestamp"] = datetime.utcnow().isoformat()

                    return cached_response

                logger.debug(
                    "rag_cache_miss",
                    cache_time_ms=round(cache_time_ms, 2),
                )

            # Step 2: Retrieve documents (hybrid search)
            retrieval_start = time.time()
            documents = await self.retrieval_service.hybrid_search(
                query=question,
                k=k * 2,  # Retrieve more for reranking
                min_score=min_score,
            )
            retrieval_time_ms = (time.time() - retrieval_start) * 1000

            logger.info(
                "rag_retrieval_complete",
                documents_retrieved=len(documents),
                retrieval_time_ms=round(retrieval_time_ms, 2),
            )

            if not documents:
                # No documents found
                logger.warning(
                    "rag_no_documents_found",
                    question=question[:100],
                    workspace=workspace,
                )
                return self._build_no_context_response(
                    question=question,
                    retrieval_time_ms=retrieval_time_ms,
                    total_time_ms=(time.time() - start_time) * 1000,
                    model=model,
                )

            # Step 3: Rerank documents (if enabled)
            rerank_time_ms = 0.0
            if self.use_rerank and len(documents) > k:
                rerank_start = time.time()
                documents = await self.rerank_service.rerank(
                    query=question,
                    documents=documents,
                    top_k=k,
                    min_score=min_score,
                )
                rerank_time_ms = (time.time() - rerank_start) * 1000

                logger.info(
                    "rag_rerank_complete",
                    documents_after_rerank=len(documents),
                    rerank_time_ms=round(rerank_time_ms, 2),
                )
            else:
                # Just take top k
                documents = documents[:k]

            # Step 4: Build context from documents
            context = self._build_context(documents)
            context_length = len(context)

            logger.debug(
                "rag_context_built",
                context_length=context_length,
                document_count=len(documents),
            )

            # Step 5: Build prompt
            prompt = self._build_prompt(question, context)
            prompt_length = len(prompt)

            logger.debug(
                "rag_prompt_built",
                prompt_length=prompt_length,
            )

            # Step 6: Generate response
            generation_start = time.time()

            if stream:
                # Return streaming response
                return self._generate_streaming_response(
                    prompt=prompt,
                    question=question,
                    documents=documents,
                    workspace=workspace,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    start_time=start_time,
                    retrieval_time_ms=retrieval_time_ms,
                    rerank_time_ms=rerank_time_ms,
                    context_length=context_length,
                )
            else:
                # Non-streaming response
                response_text = await self._generate_response(
                    prompt=prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                generation_time_ms = (time.time() - generation_start) * 1000

                logger.info(
                    "rag_generation_complete",
                    generation_time_ms=round(generation_time_ms, 2),
                    response_length=len(response_text),
                )

                # Step 7: Build final response
                total_time_ms = (time.time() - start_time) * 1000

                final_response = self._build_response(
                    response_text=response_text,
                    documents=documents,
                    cached=False,
                    retrieval_time_ms=retrieval_time_ms,
                    rerank_time_ms=rerank_time_ms,
                    generation_time_ms=generation_time_ms,
                    total_time_ms=total_time_ms,
                    context_length=context_length,
                    model=model,
                )

                # Step 8: Cache response (if enabled)
                if self.use_cache:
                    await self.cache_service.set(
                        query=question,
                        response=final_response,
                        workspace=workspace,
                    )
                    logger.debug("rag_response_cached", workspace=workspace)

                logger.info(
                    "rag_query_complete",
                    total_time_ms=round(total_time_ms, 2),
                    cached=False,
                )

                return final_response

        except ValueError as e:
            logger.error("rag_validation_error", error=str(e))
            raise

        except Exception as e:
            logger.error(
                "rag_query_error",
                error=str(e),
                error_type=type(e).__name__,
                question_length=len(question),
            )
            raise Exception(f"RAG query failed: {str(e)}")

    def _build_context(self, documents: List[Dict[str, Any]], max_chars_per_doc: int = 300) -> str:
        """
        Build context string from retrieved documents.

        Args:
            documents: List of retrieved documents
            max_chars_per_doc: Maximum characters per document (default: 300)

        Returns:
            Formatted context string
        """
        context_parts = []

        for i, doc in enumerate(documents, 1):
            text = doc.get("text", "")
            metadata = doc.get("metadata", {})
            score = doc.get("score", 0.0)

            # Truncate text if too long
            if len(text) > max_chars_per_doc:
                text = text[:max_chars_per_doc] + "..."

            # Format: [Source 1] (score: 0.85): Document text...
            source_info = f"[Source {i}]"
            if metadata:
                # Add source metadata if available
                source = metadata.get("source", "")
                if source:
                    source_info = f"[Source {i}: {source}]"

            context_parts.append(
                f"{source_info} (relevance: {score:.2f}): {text}"
            )

        return "\n\n".join(context_parts)

    def _build_prompt(self, question: str, context: str) -> str:
        """
        Create RAG prompt with retrieved context.

        Args:
            question: User question
            context: Retrieved context

        Returns:
            Formatted prompt
        """
        return self.prompt_template.format(
            context=context,
            question=question,
        )

    async def _generate_response(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Generate response from Ollama (non-streaming).

        Args:
            prompt: Full prompt with context
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated response text
        """
        try:
            result = await self.ollama_service.generate(
                prompt=prompt,
                model=model,
                system=self.system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )

            return result.get("response", "")

        except Exception as e:
            logger.error(
                "rag_generation_error",
                error=str(e),
                model=model,
            )
            raise

    async def _generate_streaming_response(
        self,
        prompt: str,
        question: str,
        documents: List[Dict[str, Any]],
        workspace: str,
        model: str,
        temperature: float,
        max_tokens: int,
        start_time: float,
        retrieval_time_ms: float,
        rerank_time_ms: float,
        context_length: int,
    ) -> AsyncIterator[str]:
        """
        Generate streaming response with SSE events.

        Yields SSE events containing tokens and final metadata.

        Args:
            prompt: Full prompt with context
            question: Original question
            documents: Retrieved documents
            workspace: Workspace identifier
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            start_time: Query start timestamp
            retrieval_time_ms: Retrieval time in ms
            rerank_time_ms: Reranking time in ms
            context_length: Context string length

        Yields:
            SSE-formatted event strings
        """
        try:
            generation_start = time.time()
            full_response = ""

            # Stream from Ollama via StreamService
            async for sse_event in self.stream_service.stream_response(
                ollama_service=self.ollama_service,
                prompt=prompt,
                system=self.system_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                # Parse event to track full response
                if '"token"' in sse_event:
                    import json
                    try:
                        event_data = json.loads(sse_event.replace("data: ", "").strip())
                        token = event_data.get("token", "")
                        full_response += token
                    except:
                        pass

                yield sse_event

            # After streaming completes, cache the full response
            generation_time_ms = (time.time() - generation_start) * 1000
            total_time_ms = (time.time() - start_time) * 1000

            if self.use_cache and full_response:
                # Build response for caching
                cached_response = self._build_response(
                    response_text=full_response,
                    documents=documents,
                    cached=False,
                    retrieval_time_ms=retrieval_time_ms,
                    rerank_time_ms=rerank_time_ms,
                    generation_time_ms=generation_time_ms,
                    total_time_ms=total_time_ms,
                    context_length=context_length,
                    model=model,
                )

                await self.cache_service.set(
                    query=question,
                    response=cached_response,
                    workspace=workspace,
                )

                logger.debug("rag_streaming_response_cached", workspace=workspace)

            logger.info(
                "rag_streaming_complete",
                total_time_ms=round(total_time_ms, 2),
                response_length=len(full_response),
            )

        except Exception as e:
            logger.error(
                "rag_streaming_error",
                error=str(e),
                model=model,
            )
            # Yield error event
            import json
            error_event = f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
            yield error_event

    def _build_response(
        self,
        response_text: str,
        documents: List[Dict[str, Any]],
        cached: bool,
        retrieval_time_ms: float,
        rerank_time_ms: float,
        generation_time_ms: float,
        total_time_ms: float,
        context_length: int,
        model: str,
    ) -> Dict[str, Any]:
        """
        Build final response dictionary with metadata.

        Args:
            response_text: Generated response
            documents: Retrieved documents
            cached: Whether response was cached
            retrieval_time_ms: Retrieval time
            rerank_time_ms: Reranking time
            generation_time_ms: Generation time
            total_time_ms: Total pipeline time
            context_length: Context string length
            model: Model used

        Returns:
            Complete response dictionary
        """
        # Build sources list
        sources = []
        for i, doc in enumerate(documents, 1):
            sources.append({
                "id": doc.get("id", f"doc_{i}"),
                "text": doc.get("text", "")[:200] + "...",  # Truncate for brevity
                "score": round(doc.get("score", 0.0), 4),
                "metadata": doc.get("metadata", {}),
                "method": doc.get("method", "unknown"),
            })

        return {
            "response": response_text,
            "sources": sources,
            "metadata": {
                "cached": cached,
                "retrieval_method": "hybrid",
                "retrieval_time_ms": round(retrieval_time_ms, 2),
                "rerank_time_ms": round(rerank_time_ms, 2) if rerank_time_ms > 0 else 0.0,
                "generation_time_ms": round(generation_time_ms, 2),
                "total_time_ms": round(total_time_ms, 2),
                "model": model,
                "context_length": context_length,
                "source_count": len(documents),
                "use_cache": self.use_cache,
                "use_rerank": self.use_rerank,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _build_no_context_response(
        self,
        question: str,
        retrieval_time_ms: float,
        total_time_ms: float,
        model: str,
    ) -> Dict[str, Any]:
        """
        Build response when no documents are found.

        Args:
            question: Original question
            retrieval_time_ms: Retrieval time
            total_time_ms: Total time
            model: Model name

        Returns:
            Response indicating no context found
        """
        return {
            "response": "I couldn't find any relevant information in the knowledge base to answer your question. Please try rephrasing or ask a different question.",
            "sources": [],
            "metadata": {
                "cached": False,
                "retrieval_method": "hybrid",
                "retrieval_time_ms": round(retrieval_time_ms, 2),
                "rerank_time_ms": 0.0,
                "generation_time_ms": 0.0,
                "total_time_ms": round(total_time_ms, 2),
                "model": model,
                "context_length": 0,
                "source_count": 0,
                "use_cache": self.use_cache,
                "use_rerank": self.use_rerank,
                "no_context_found": True,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all sub-services.

        Returns:
            Health status for each service
        """
        logger.info("rag_health_check_start")

        health_status = {
            "cache": False,
            "ollama": False,
            "retrieval": False,
            "rerank": False,
            "overall": False,
        }

        try:
            # Check cache service
            if self.use_cache:
                health_status["cache"] = await self.cache_service.health_check()
            else:
                health_status["cache"] = "disabled"

            # Check Ollama service
            health_status["ollama"] = await self.ollama_service.health_check()

            # Check retrieval service
            health_status["retrieval"] = await self.retrieval_service.health_check()

            # Check rerank service
            if self.use_rerank:
                health_status["rerank"] = await self.rerank_service.health_check()
            else:
                health_status["rerank"] = "disabled"

            # Overall health
            critical_services = ["ollama", "retrieval"]
            health_status["overall"] = all(
                health_status[svc] for svc in critical_services
            )

            logger.info(
                "rag_health_check_complete",
                status=health_status,
            )

            return health_status

        except Exception as e:
            logger.error("rag_health_check_error", error=str(e))
            return health_status

    async def get_stats(self) -> Dict[str, Any]:
        """
        Aggregate statistics from all services.

        Returns:
            Combined statistics dictionary
        """
        logger.info("rag_stats_start")

        try:
            stats = {
                "cache": {},
                "retrieval": {},
                "model": self.model,
                "use_cache": self.use_cache,
                "use_rerank": self.use_rerank,
            }

            # Cache stats
            if self.use_cache:
                stats["cache"] = await self.cache_service.get_stats()

            # Retrieval stats
            stats["retrieval"] = await self.retrieval_service.get_collection_info()

            logger.info("rag_stats_complete", stats=stats)

            return stats

        except Exception as e:
            logger.error("rag_stats_error", error=str(e))
            return {}

    async def close(self):
        """Close all service connections."""
        logger.info("rag_service_v2_closing")

        try:
            if self.cache_service:
                await self.cache_service.close()

            if self.ollama_service:
                await self.ollama_service.close()

            if self.retrieval_service:
                await self.retrieval_service.close()

            if self.rerank_service:
                await self.rerank_service.close()

            logger.info("rag_service_v2_closed")

        except Exception as e:
            logger.error("rag_service_v2_close_error", error=str(e))

    # ========================================================================
    # V1 Compatibility Methods
    # ========================================================================

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
        V1-compatible chat method that wraps the query method.

        This allows RAG V2 to work with the existing V1 router endpoints
        without modification.

        Args:
            message: User message
            workspace_slug: Workspace identifier (not used in V2, all docs in ChromaDB)
            mode: Chat mode ('chat' or 'query') - not used in V2
            temperature: LLM temperature
            max_tokens: Maximum response tokens
            session_id: Session ID (not used in V2 currently)

        Returns:
            Dict with response, sources, session_id, timestamp, model
        """
        logger.info("chat_v1_compat_request",
                   workspace=workspace_slug,
                   mode=mode,
                   message_length=len(message))

        try:
            # Call query method
            result = await self.query(
                question=message,
                workspace=workspace_slug,
                k=5,
                stream=False,
                temperature=temperature,
                max_tokens=max_tokens,
                min_score=0.0,
                model=None
            )

            # Transform to V1 format
            response = {
                "response": result["response"],
                "sources": result.get("sources", []),
                "session_id": session_id or "default",  # V2 doesn't track sessions yet
                "timestamp": result["timestamp"],
                "model": result.get("metadata", {}).get("model", self.model)
            }

            logger.info("chat_v1_compat_success",
                       response_length=len(response["response"]),
                       sources_count=len(response["sources"]))

            return response

        except Exception as e:
            logger.error("chat_v1_compat_error", error=str(e))
            raise

    async def get_workspaces(self) -> List[Dict[str, Any]]:
        """
        V1-compatible method to list workspaces.

        In V2, we don't have workspaces - all documents are in ChromaDB.
        Returns a stub response for compatibility.

        Returns:
            List with single "greenfrog" workspace
        """
        logger.info("get_workspaces_v1_compat")

        # Get collection info from retrieval service
        try:
            collection_info = await self.retrieval_service.get_collection_info()
            doc_count = collection_info.get("document_count", 0)
        except Exception:
            doc_count = 0

        return [{
            "id": "greenfrog",
            "name": "GreenFrog Knowledge Base",
            "slug": "greenfrog",
            "documents": doc_count,
            "description": "RAG V2 unified knowledge base"
        }]

    async def get_workspace_stats(self, workspace_slug: str) -> Dict[str, Any]:
        """
        V1-compatible method to get workspace statistics.

        In V2, returns collection statistics from ChromaDB.

        Args:
            workspace_slug: Workspace identifier (ignored in V2)

        Returns:
            Workspace statistics
        """
        logger.info("get_workspace_stats_v1_compat", workspace=workspace_slug)

        try:
            # Get collection info
            collection_info = await self.retrieval_service.get_collection_info()

            # Get cache stats if enabled
            cache_stats = {}
            if self.use_cache:
                cache_stats = await self.cache_service.get_stats()

            return {
                "id": "greenfrog",
                "name": "GreenFrog Knowledge Base",
                "slug": "greenfrog",
                "documents": collection_info.get("document_count", 0),
                "vectors": collection_info.get("document_count", 0),
                "model": self.model,
                "embedding_model": "nomic-embed-text:latest",
                "cache_enabled": self.use_cache,
                "rerank_enabled": self.use_rerank,
                "cache_stats": cache_stats
            }

        except Exception as e:
            logger.error("get_workspace_stats_v1_compat_error", error=str(e))
            return {
                "id": "greenfrog",
                "name": "GreenFrog Knowledge Base",
                "slug": "greenfrog",
                "error": str(e)
            }


# ========================================================================
# Singleton Instance Management
# ========================================================================

_rag_instance_v2: Optional[RAGServiceV2] = None


def get_rag_service_v2() -> RAGServiceV2:
    """
    Get or create RAG Service V2 singleton instance.

    This creates all necessary sub-services and initializes the
    complete RAG V2 pipeline with default configuration.

    Returns:
        RAGServiceV2 instance
    """
    global _rag_instance_v2
    
    if _rag_instance_v2 is None:
        logger.info("initializing_rag_v2_singleton")
        
        # Create sub-services
        cache_service = CacheService()
        ollama_service = OllamaService()
        retrieval_service = RetrievalService(ollama_service=ollama_service)
        rerank_service = RerankService()
        stream_service = StreamService()
        
        # Create RAG service
        _rag_instance_v2 = RAGServiceV2(
            cache_service=cache_service,
            ollama_service=ollama_service,
            retrieval_service=retrieval_service,
            rerank_service=rerank_service,
            stream_service=stream_service,
        )
        
        logger.info("rag_v2_singleton_initialized",
                   model=_rag_instance_v2.model,
                   use_cache=_rag_instance_v2.use_cache,
                   use_rerank=_rag_instance_v2.use_rerank)
    
    return _rag_instance_v2
