"""
Hybrid Retrieval Service for GreenFrog RAG
Combines BM25 keyword search with semantic vector search using Reciprocal Rank Fusion
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
import structlog
from rank_bm25 import BM25Okapi
import numpy as np
import os
from collections import defaultdict
import chromadb

logger = structlog.get_logger(__name__)


class RetrievalService:
    """
    Hybrid retrieval combining BM25 keyword search and semantic vector search.

    Features:
    - BM25 for keyword-based ranking
    - Semantic search via ChromaDB
    - Reciprocal Rank Fusion (RRF) for result combination
    - Automatic document loading and indexing
    - Query embedding generation via Ollama
    """

    def __init__(
        self,
        chromadb_url: str = None,
        ollama_service = None,
        collection_name: str = "greenfrog",
        embedding_model: str = "nomic-embed-text:latest",
        timeout: float = 30.0
    ):
        """
        Initialize hybrid retrieval service.

        Args:
            chromadb_url: ChromaDB API URL (default from env)
            ollama_service: OllamaService instance for embeddings
            collection_name: ChromaDB collection name
            embedding_model: Ollama embedding model name
            timeout: Request timeout in seconds
        """
        self.chromadb_url = chromadb_url or os.getenv(
            "CHROMADB_URL",
            "http://chromadb:8000"
        )
        self.chromadb_url = self.chromadb_url.rstrip("/")
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.timeout = timeout

        # Ollama service for embedding generation
        self.ollama_service = ollama_service

        # ChromaDB client (lazy initialized)
        self._chroma_client: Optional[chromadb.HttpClient] = None
        self._collection: Optional[chromadb.Collection] = None

        # BM25 index (lazy initialized)
        self._bm25_index: Optional[BM25Okapi] = None
        self._documents: List[Dict[str, Any]] = []
        self._document_texts: List[str] = []
        self._tokenized_corpus: List[List[str]] = []

        # Cache for loaded documents
        self._documents_loaded = False

        logger.info(
            "retrieval_service_init",
            chromadb_url=self.chromadb_url,
            collection=collection_name,
            embedding_model=embedding_model
        )

    def _get_chroma_client(self) -> chromadb.HttpClient:
        """Get or create ChromaDB HTTP client."""
        if self._chroma_client is None:
            # Parse host and port from URL
            url_parts = self.chromadb_url.replace("http://", "").replace("https://", "").split(":")
            host = url_parts[0]
            port = int(url_parts[1]) if len(url_parts) > 1 else 8000

            self._chroma_client = chromadb.HttpClient(
                host=host,
                port=port
            )
            logger.debug("chromadb_client_created", host=host, port=port)
        return self._chroma_client

    def _get_collection(self) -> chromadb.Collection:
        """Get or create ChromaDB collection."""
        if self._collection is None:
            client = self._get_chroma_client()
            try:
                self._collection = client.get_collection(name=self.collection_name)
                logger.debug("collection_retrieved", name=self.collection_name)
            except Exception as e:
                logger.error("collection_not_found", name=self.collection_name, error=str(e))
                raise Exception(f"Collection '{self.collection_name}' not found. Please ensure it exists in ChromaDB.")
        return self._collection

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """
        Simple tokenization for BM25.

        Args:
            text: Input text

        Returns:
            List of tokens (lowercased, split by whitespace)
        """
        return text.lower().split()

    async def load_documents(self, force_reload: bool = False) -> int:
        """
        Load all documents from ChromaDB for BM25 indexing.

        Args:
            force_reload: Force reload even if already loaded

        Returns:
            Number of documents loaded
        """
        if self._documents_loaded and not force_reload:
            logger.debug("documents_already_loaded", count=len(self._documents))
            return len(self._documents)

        try:
            logger.info("loading_documents_from_chromadb", collection=self.collection_name)

            collection = self._get_collection()

            # Get all documents from collection
            result = collection.get(
                include=["documents", "metadatas", "embeddings"]
            )

            ids = result.get("ids", [])
            documents = result.get("documents", [])
            metadatas = result.get("metadatas", [])
            embeddings = result.get("embeddings", [])

            if not ids:
                logger.warning("no_documents_found", collection=self.collection_name)
                return 0

            # Build document list
            self._documents = []
            self._document_texts = []

            for i, doc_id in enumerate(ids):
                doc_text = documents[i] if i < len(documents) else ""
                doc_metadata = metadatas[i] if i < len(metadatas) else {}
                doc_embedding = embeddings[i] if i < len(embeddings) else None

                self._documents.append({
                    "id": doc_id,
                    "text": doc_text,
                    "metadata": doc_metadata,
                    "embedding": doc_embedding
                })
                self._document_texts.append(doc_text)

            # Build BM25 index
            self._tokenized_corpus = [
                self._tokenize(text) for text in self._document_texts
            ]
            self._bm25_index = BM25Okapi(self._tokenized_corpus)

            self._documents_loaded = True

            logger.info(
                "documents_loaded",
                count=len(self._documents),
                collection=self.collection_name
            )

            return len(self._documents)

        except Exception as e:
            logger.error("load_documents_error", error=str(e))
            raise Exception(f"Failed to load documents: {str(e)}")

    async def _generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for query using Ollama.

        Args:
            query: Query text

        Returns:
            Query embedding vector
        """
        if not self.ollama_service:
            raise ValueError("OllamaService not provided - cannot generate embeddings")

        try:
            logger.debug("generating_query_embedding", query_length=len(query))

            embedding = await self.ollama_service.embeddings(
                text=query,
                model=self.embedding_model
            )

            logger.debug("query_embedding_generated", dimension=len(embedding))
            return embedding

        except Exception as e:
            logger.error("query_embedding_error", error=str(e))
            raise Exception(f"Failed to generate query embedding: {str(e)}")

    async def _semantic_search(
        self,
        query_embedding: List[float],
        k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic vector search via ChromaDB.

        Args:
            query_embedding: Query embedding vector
            k: Number of results to retrieve

        Returns:
            List of documents with similarity scores
        """
        try:
            logger.debug("semantic_search_start", k=k)

            collection = self._get_collection()

            # Query ChromaDB with embedding
            result = collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )

            # Parse results (ChromaDB returns nested lists)
            ids = result.get("ids", [[]])[0]
            documents = result.get("documents", [[]])[0]
            metadatas = result.get("metadatas", [[]])[0]
            distances = result.get("distances", [[]])[0]

            # Build result list with scores
            # ChromaDB returns distances (lower is better), convert to similarity
            results = []
            for i, doc_id in enumerate(ids):
                distance = distances[i] if i < len(distances) else 1.0
                # Convert distance to similarity (1 / (1 + distance))
                similarity = 1.0 / (1.0 + distance)

                results.append({
                    "id": doc_id,
                    "text": documents[i] if i < len(documents) else "",
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "score": similarity,
                    "distance": distance,
                    "method": "semantic"
                })

            logger.debug("semantic_search_complete", results_count=len(results))
            return results

        except Exception as e:
            logger.error("semantic_search_error", error=str(e))
            raise Exception(f"Semantic search failed: {str(e)}")

    async def _bm25_search(
        self,
        query: str,
        k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Perform BM25 keyword search.

        Args:
            query: Query text
            k: Number of results to retrieve

        Returns:
            List of documents with BM25 scores
        """
        try:
            # Ensure documents are loaded
            if not self._documents_loaded:
                await self.load_documents()

            if not self._bm25_index:
                logger.warning("bm25_index_not_available")
                return []

            logger.debug("bm25_search_start", k=k)

            # Tokenize query
            tokenized_query = self._tokenize(query)

            # Get BM25 scores
            scores = self._bm25_index.get_scores(tokenized_query)

            # Get top k indices
            top_indices = np.argsort(scores)[::-1][:k]

            # Build results
            results = []
            for idx in top_indices:
                if idx >= len(self._documents):
                    continue

                doc = self._documents[idx]
                score = float(scores[idx])

                # Only include if score > 0
                if score > 0:
                    results.append({
                        "id": doc["id"],
                        "text": doc["text"],
                        "metadata": doc["metadata"],
                        "score": score,
                        "method": "bm25"
                    })

            logger.debug("bm25_search_complete", results_count=len(results))
            return results

        except Exception as e:
            logger.error("bm25_search_error", error=str(e))
            # Don't raise - allow hybrid search to continue with only semantic results
            return []

    @staticmethod
    def _reciprocal_rank_fusion(
        semantic_results: List[Dict[str, Any]],
        bm25_results: List[Dict[str, Any]],
        k: int = 60,
        weights: Tuple[float, float] = (0.5, 0.5)
    ) -> List[Dict[str, Any]]:
        """
        Combine semantic and BM25 results using Reciprocal Rank Fusion (RRF).

        RRF formula: RRF_score(d) = sum_r [ weight_r / (k + rank_r(d)) ]
        where r is each ranking method, k is a constant (typically 60).

        Args:
            semantic_results: Results from semantic search
            bm25_results: Results from BM25 search
            k: RRF constant (typically 60)
            weights: Tuple of (semantic_weight, bm25_weight)

        Returns:
            Combined and reranked results
        """
        logger.debug(
            "rrf_start",
            semantic_count=len(semantic_results),
            bm25_count=len(bm25_results),
            k=k
        )

        # Build document ID to data mapping
        doc_map: Dict[str, Dict[str, Any]] = {}

        # Track RRF scores
        rrf_scores: Dict[str, float] = defaultdict(float)

        # Process semantic results
        semantic_weight = weights[0]
        for rank, result in enumerate(semantic_results):
            doc_id = result["id"]
            rrf_scores[doc_id] += semantic_weight * (1.0 / (k + rank + 1))

            if doc_id not in doc_map:
                doc_map[doc_id] = result.copy()
                doc_map[doc_id]["semantic_score"] = result.get("score", 0.0)
                doc_map[doc_id]["semantic_rank"] = rank + 1

        # Process BM25 results
        bm25_weight = weights[1]
        for rank, result in enumerate(bm25_results):
            doc_id = result["id"]
            rrf_scores[doc_id] += bm25_weight * (1.0 / (k + rank + 1))

            if doc_id not in doc_map:
                doc_map[doc_id] = result.copy()

            doc_map[doc_id]["bm25_score"] = result.get("score", 0.0)
            doc_map[doc_id]["bm25_rank"] = rank + 1

        # Combine and sort by RRF score
        combined_results = []
        for doc_id, doc in doc_map.items():
            doc["rrf_score"] = rrf_scores[doc_id]
            doc["method"] = "hybrid"
            combined_results.append(doc)

        # Sort by RRF score (descending)
        combined_results.sort(key=lambda x: x["rrf_score"], reverse=True)

        logger.debug("rrf_complete", combined_count=len(combined_results))
        return combined_results

    async def hybrid_search(
        self,
        query: str,
        k: int = 10,
        rrf_k: int = 60,
        weights: Tuple[float, float] = (0.5, 0.5),
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining BM25 and semantic search.

        Args:
            query: Search query
            k: Number of final results to return
            rrf_k: RRF constant (typically 60)
            weights: Tuple of (semantic_weight, bm25_weight)
            min_score: Minimum RRF score threshold

        Returns:
            Combined and reranked search results
        """
        try:
            logger.info(
                "hybrid_search_start",
                query_length=len(query),
                k=k
            )

            # Generate query embedding
            query_embedding = await self._generate_query_embedding(query)

            # Retrieve more results than k for better fusion
            retrieve_k = min(k * 2, 50)

            # Run both searches in parallel
            semantic_task = self._semantic_search(query_embedding, retrieve_k)
            bm25_task = self._bm25_search(query, retrieve_k)

            semantic_results, bm25_results = await asyncio.gather(
                semantic_task,
                bm25_task,
                return_exceptions=True
            )

            # Handle exceptions
            if isinstance(semantic_results, Exception):
                logger.error("semantic_search_failed", error=str(semantic_results))
                semantic_results = []

            if isinstance(bm25_results, Exception):
                logger.error("bm25_search_failed", error=str(bm25_results))
                bm25_results = []

            # If both failed, raise exception
            if not semantic_results and not bm25_results:
                raise Exception("Both semantic and BM25 search failed")

            # Apply RRF
            combined_results = self._reciprocal_rank_fusion(
                semantic_results,
                bm25_results,
                k=rrf_k,
                weights=weights
            )

            # Filter by minimum score
            if min_score > 0:
                combined_results = [
                    r for r in combined_results
                    if r.get("rrf_score", 0.0) >= min_score
                ]

            # Return top k
            final_results = combined_results[:k]

            logger.info(
                "hybrid_search_complete",
                results_count=len(final_results),
                semantic_count=len(semantic_results),
                bm25_count=len(bm25_results)
            )

            return final_results

        except Exception as e:
            logger.error("hybrid_search_error", error=str(e))
            raise Exception(f"Hybrid search failed: {str(e)}")

    async def semantic_search(
        self,
        query: str,
        k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic-only search.

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            Semantic search results
        """
        query_embedding = await self._generate_query_embedding(query)
        return await self._semantic_search(query_embedding, k)

    async def keyword_search(
        self,
        query: str,
        k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Perform BM25 keyword-only search.

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            BM25 search results
        """
        return await self._bm25_search(query, k)

    async def get_collection_info(self) -> Dict[str, Any]:
        """
        Get ChromaDB collection information.

        Returns:
            Collection metadata and stats
        """
        try:
            collection = self._get_collection()

            # Get collection count
            count = collection.count()

            # Get collection metadata
            metadata = collection.metadata if hasattr(collection, 'metadata') else {}

            info = {
                "name": self.collection_name,
                "count": count,
                "metadata": metadata
            }

            logger.info("collection_info", collection=self.collection_name, info=info)
            return info

        except Exception as e:
            logger.error("get_collection_info_error", error=str(e))
            return {}

    async def health_check(self) -> bool:
        """
        Check if retrieval service is healthy.

        Returns:
            True if ChromaDB is reachable and documents are loaded
        """
        try:
            # Check ChromaDB connection
            client = self._get_chroma_client()
            heartbeat = client.heartbeat()

            if not heartbeat:
                return False

            # Ensure collection exists
            collection = self._get_collection()

            # Ensure documents are loaded
            if not self._documents_loaded:
                await self.load_documents()

            logger.info("retrieval_health_check_passed", doc_count=len(self._documents))
            return True

        except Exception as e:
            logger.error("retrieval_health_check_failed", error=str(e))
            return False

    async def close(self):
        """Close ChromaDB client and cleanup resources."""
        # ChromaDB client doesn't need explicit closing
        logger.info("retrieval_service_closed")


# Global retrieval service instance
_retrieval_instance: Optional[RetrievalService] = None


def get_retrieval_service(
    chromadb_url: str = None,
    ollama_service = None,
    collection_name: str = "greenfrog"
) -> RetrievalService:
    """
    Get or create retrieval service instance.

    Args:
        chromadb_url: ChromaDB API URL
        ollama_service: OllamaService instance
        collection_name: ChromaDB collection name

    Returns:
        RetrievalService instance
    """
    global _retrieval_instance
    if _retrieval_instance is None:
        _retrieval_instance = RetrievalService(
            chromadb_url=chromadb_url,
            ollama_service=ollama_service,
            collection_name=collection_name
        )
    return _retrieval_instance
