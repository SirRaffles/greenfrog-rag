"""
Redis Semantic Caching Service
Implements embedding-based similarity caching for RAG queries
"""

import json
import hashlib
import numpy as np
from typing import Optional, Dict, Any, List
from datetime import timedelta
import redis.asyncio as redis
import structlog
from sentence_transformers import SentenceTransformer
import os

logger = structlog.get_logger(__name__)


class CacheService:
    """
    Semantic cache using Redis and embeddings for similarity-based lookup.

    Features:
    - Embedding-based similarity matching
    - Configurable similarity threshold
    - TTL support for cache expiration
    - Fallback to exact match if embedding fails
    """

    def __init__(
        self,
        redis_url: str = None,
        embedding_model: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.95,
        ttl_seconds: int = 3600,  # 1 hour default
    ):
        """
        Initialize cache service.

        Args:
            redis_url: Redis connection URL (default from env)
            embedding_model: SentenceTransformer model name
            similarity_threshold: Minimum cosine similarity for cache hit (0-1)
            ttl_seconds: Cache entry TTL in seconds
        """
        self.redis_url = redis_url or os.getenv(
            "REDIS_URL",
            "redis://greenfrog-redis:6379"
        )
        self.similarity_threshold = similarity_threshold
        self.ttl = timedelta(seconds=ttl_seconds)

        # Redis client (lazy initialized)
        self._redis: Optional[redis.Redis] = None

        # Embedding model for semantic similarity
        self.embedding_model_name = embedding_model
        self._embedding_model: Optional[SentenceTransformer] = None

        logger.info(
            "cache_service_init",
            redis_url=self.redis_url,
            embedding_model=embedding_model,
            similarity_threshold=similarity_threshold,
            ttl_seconds=ttl_seconds
        )

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("redis_connected", url=self.redis_url)
        return self._redis

    def _get_embedding_model(self) -> SentenceTransformer:
        """Get or load embedding model."""
        if self._embedding_model is None:
            logger.info("loading_embedding_model", model=self.embedding_model_name)
            self._embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info("embedding_model_loaded")
        return self._embedding_model

    def _generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding vector for text.

        Args:
            text: Input text

        Returns:
            Embedding vector as numpy array
        """
        model = self._get_embedding_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            a: First vector
            b: Second vector

        Returns:
            Cosine similarity (0-1)
        """
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    @staticmethod
    def _hash_query(query: str, workspace: str = "default") -> str:
        """
        Create a deterministic hash for query + workspace.
        Used for exact match lookup.

        Args:
            query: Query text
            workspace: Workspace identifier

        Returns:
            Hash string
        """
        key = f"{workspace}:{query}"
        return hashlib.sha256(key.encode()).hexdigest()

    async def get(
        self,
        query: str,
        workspace: str = "default",
        use_semantic: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached response for query.

        First tries exact match, then semantic similarity if enabled.

        Args:
            query: User query
            workspace: Workspace identifier
            use_semantic: Whether to use semantic similarity search

        Returns:
            Cached response dict or None if no match
        """
        try:
            r = await self._get_redis()

            # Try exact match first (fastest)
            exact_key = self._hash_query(query, workspace)
            exact_match = await r.get(f"cache:exact:{exact_key}")

            if exact_match:
                logger.info(
                    "cache_hit_exact",
                    query_length=len(query),
                    workspace=workspace
                )
                return json.loads(exact_match)

            # Try semantic similarity if enabled
            if use_semantic:
                query_embedding = self._generate_embedding(query)

                # Get all cached embeddings for this workspace
                pattern = f"cache:embedding:{workspace}:*"
                keys = []
                async for key in r.scan_iter(match=pattern, count=100):
                    keys.append(key)

                if not keys:
                    logger.debug("cache_miss_no_embeddings", workspace=workspace)
                    return None

                # Find most similar cached query
                best_similarity = 0.0
                best_key = None

                for key in keys:
                    cached_embedding_str = await r.get(key)
                    if not cached_embedding_str:
                        continue

                    cached_embedding = np.array(json.loads(cached_embedding_str))
                    similarity = self._cosine_similarity(query_embedding, cached_embedding)

                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_key = key

                # Check if similarity exceeds threshold
                if best_similarity >= self.similarity_threshold:
                    # Extract response key from embedding key
                    response_key = best_key.replace(
                        "cache:embedding:",
                        "cache:response:"
                    )
                    response = await r.get(response_key)

                    if response:
                        logger.info(
                            "cache_hit_semantic",
                            similarity=round(best_similarity, 4),
                            query_length=len(query),
                            workspace=workspace
                        )
                        return json.loads(response)

            logger.debug("cache_miss", query_length=len(query), workspace=workspace)
            return None

        except Exception as e:
            logger.error("cache_get_error", error=str(e), query_length=len(query))
            return None

    async def set(
        self,
        query: str,
        response: Dict[str, Any],
        workspace: str = "default"
    ) -> bool:
        """
        Cache response for query.

        Stores both exact match and embedding for semantic lookup.

        Args:
            query: User query
            response: Response to cache
            workspace: Workspace identifier

        Returns:
            True if cached successfully
        """
        try:
            r = await self._get_redis()

            # Store exact match
            exact_key = self._hash_query(query, workspace)
            await r.setex(
                f"cache:exact:{exact_key}",
                self.ttl,
                json.dumps(response)
            )

            # Store embedding and response for semantic lookup
            query_embedding = self._generate_embedding(query)
            embedding_key = f"cache:embedding:{workspace}:{exact_key}"
            response_key = f"cache:response:{workspace}:{exact_key}"

            await r.setex(
                embedding_key,
                self.ttl,
                json.dumps(query_embedding.tolist())
            )
            await r.setex(
                response_key,
                self.ttl,
                json.dumps(response)
            )

            logger.info(
                "cache_set",
                query_length=len(query),
                workspace=workspace,
                ttl_seconds=self.ttl.total_seconds()
            )
            return True

        except Exception as e:
            logger.error("cache_set_error", error=str(e), query_length=len(query))
            return False

    async def invalidate(
        self,
        query: Optional[str] = None,
        workspace: str = "default"
    ) -> int:
        """
        Invalidate cache entries.

        Args:
            query: Specific query to invalidate (None = all workspace entries)
            workspace: Workspace identifier

        Returns:
            Number of keys deleted
        """
        try:
            r = await self._get_redis()

            if query:
                # Invalidate specific query
                exact_key = self._hash_query(query, workspace)
                keys_to_delete = [
                    f"cache:exact:{exact_key}",
                    f"cache:embedding:{workspace}:{exact_key}",
                    f"cache:response:{workspace}:{exact_key}"
                ]
                count = await r.delete(*keys_to_delete)
                logger.info("cache_invalidate_query", count=count, workspace=workspace)
                return count
            else:
                # Invalidate all workspace entries
                patterns = [
                    f"cache:exact:*",  # Would need workspace in key for better filtering
                    f"cache:embedding:{workspace}:*",
                    f"cache:response:{workspace}:*"
                ]
                count = 0
                for pattern in patterns:
                    keys = []
                    async for key in r.scan_iter(match=pattern, count=100):
                        keys.append(key)
                    if keys:
                        count += await r.delete(*keys)

                logger.info("cache_invalidate_workspace", count=count, workspace=workspace)
                return count

        except Exception as e:
            logger.error("cache_invalidate_error", error=str(e))
            return 0

    async def get_stats(self, workspace: str = "default") -> Dict[str, int]:
        """
        Get cache statistics for workspace.

        Args:
            workspace: Workspace identifier

        Returns:
            Dict with cache stats (total_entries, total_embeddings, etc.)
        """
        try:
            r = await self._get_redis()

            # Count entries by pattern
            exact_count = 0
            async for _ in r.scan_iter(match="cache:exact:*", count=100):
                exact_count += 1

            embedding_count = 0
            async for _ in r.scan_iter(match=f"cache:embedding:{workspace}:*", count=100):
                embedding_count += 1

            response_count = 0
            async for _ in r.scan_iter(match=f"cache:response:{workspace}:*", count=100):
                response_count += 1

            return {
                "exact_entries": exact_count,
                "embedding_entries": embedding_count,
                "response_entries": response_count,
                "workspace": workspace
            }

        except Exception as e:
            logger.error("cache_stats_error", error=str(e))
            return {}

    async def health_check(self) -> bool:
        """
        Check if cache service is healthy.

        Returns:
            True if Redis is reachable
        """
        try:
            r = await self._get_redis()
            await r.ping()
            return True
        except Exception as e:
            logger.error("cache_health_check_failed", error=str(e))
            return False

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            logger.info("redis_connection_closed")
