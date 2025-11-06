"""
RAG Service V2 Example Usage

Demonstrates how to use the RAGServiceV2 orchestrator with all sub-services.

This example shows:
1. Service initialization
2. Non-streaming query
3. Streaming query
4. Health checks
5. Statistics gathering
6. Proper cleanup
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services import (
    CacheService,
    OllamaService,
    RetrievalService,
    RerankService,
    StreamService,
    RAGServiceV2,
)


async def example_non_streaming():
    """Example: Non-streaming RAG query."""
    print("\n" + "="*80)
    print("NON-STREAMING QUERY EXAMPLE")
    print("="*80 + "\n")

    # Initialize services
    cache_service = CacheService(
        similarity_threshold=0.95,
        ttl_seconds=3600,
    )

    ollama_service = OllamaService(
        model="phi3:mini",
        timeout=120.0,
    )

    retrieval_service = RetrievalService(
        ollama_service=ollama_service,
        collection_name="greenfrog",
    )

    rerank_service = RerankService(
        model="score-based",
    )

    stream_service = StreamService()

    # Initialize RAG service
    rag_service = RAGServiceV2(
        cache_service=cache_service,
        ollama_service=ollama_service,
        retrieval_service=retrieval_service,
        rerank_service=rerank_service,
        stream_service=stream_service,
        model="phi3:mini",
        use_cache=True,
        use_rerank=True,
    )

    try:
        # First query (cache miss)
        print("Query 1: What is machine learning?")
        print("-" * 80)

        response1 = await rag_service.query(
            question="What is machine learning?",
            workspace="greenfrog",
            k=5,
            stream=False,
            temperature=0.7,
            max_tokens=512,
        )

        print(f"\nResponse: {response1['response'][:200]}...")
        print(f"\nSources found: {response1['metadata']['source_count']}")
        print(f"Cached: {response1['metadata']['cached']}")
        print(f"Total time: {response1['metadata']['total_time_ms']:.2f}ms")
        print(f"  - Retrieval: {response1['metadata']['retrieval_time_ms']:.2f}ms")
        print(f"  - Reranking: {response1['metadata']['rerank_time_ms']:.2f}ms")
        print(f"  - Generation: {response1['metadata']['generation_time_ms']:.2f}ms")

        # Second query - similar question (should hit cache)
        print("\n" + "="*80)
        print("Query 2: What's machine learning? (similar to query 1)")
        print("-" * 80)

        response2 = await rag_service.query(
            question="What's machine learning?",
            workspace="greenfrog",
            k=5,
            stream=False,
        )

        print(f"\nCached: {response2['metadata']['cached']}")
        if response2['metadata']['cached']:
            print(f"Cache hit! Retrieval time: {response2['metadata'].get('cache_time_ms', 0):.2f}ms")
        print(f"Total time: {response2['metadata']['total_time_ms']:.2f}ms")

    finally:
        await rag_service.close()


async def example_streaming():
    """Example: Streaming RAG query."""
    print("\n" + "="*80)
    print("STREAMING QUERY EXAMPLE")
    print("="*80 + "\n")

    # Initialize services
    ollama_service = OllamaService(model="phi3:mini")
    retrieval_service = RetrievalService(
        ollama_service=ollama_service,
        collection_name="greenfrog",
    )
    rerank_service = RerankService()
    stream_service = StreamService()
    cache_service = CacheService()

    rag_service = RAGServiceV2(
        cache_service=cache_service,
        ollama_service=ollama_service,
        retrieval_service=retrieval_service,
        rerank_service=rerank_service,
        stream_service=stream_service,
        use_cache=False,  # Disable cache for streaming demo
    )

    try:
        print("Query: Explain neural networks")
        print("-" * 80)
        print("\nStreaming response:\n")

        # Stream the response
        stream = await rag_service.query(
            question="Explain neural networks",
            workspace="greenfrog",
            k=3,
            stream=True,
            temperature=0.7,
        )

        # Process SSE events
        import json
        token_count = 0

        async for sse_event in stream:
            # Parse SSE event
            if sse_event.startswith("data: "):
                try:
                    data = json.loads(sse_event[6:])

                    if "token" in data:
                        # Print token
                        print(data["token"], end="", flush=True)
                        token_count += 1

                    elif "done" in data and data["done"]:
                        # Streaming complete
                        print("\n\n" + "-" * 80)
                        if "stats" in data:
                            stats = data["stats"]
                            print(f"\nStreaming stats:")
                            print(f"  - Tokens: {stats.get('token_count', 0)}")
                            print(f"  - Chunks: {stats.get('chunk_count', 0)}")
                            print(f"  - Elapsed: {stats.get('elapsed_ms', 0):.2f}ms")
                            print(f"  - Tokens/sec: {stats.get('tokens_per_second', 0):.2f}")

                    elif "error" in data:
                        print(f"\n\nError: {data['error']}")

                except json.JSONDecodeError:
                    pass

        print(f"\nTotal tokens printed: {token_count}")

    finally:
        await rag_service.close()


async def example_health_and_stats():
    """Example: Health checks and statistics."""
    print("\n" + "="*80)
    print("HEALTH CHECK & STATISTICS EXAMPLE")
    print("="*80 + "\n")

    # Initialize services
    ollama_service = OllamaService()
    retrieval_service = RetrievalService(
        ollama_service=ollama_service,
    )
    rerank_service = RerankService()
    stream_service = StreamService()
    cache_service = CacheService()

    rag_service = RAGServiceV2(
        cache_service=cache_service,
        ollama_service=ollama_service,
        retrieval_service=retrieval_service,
        rerank_service=rerank_service,
        stream_service=stream_service,
    )

    try:
        # Health check
        print("Running health check...")
        print("-" * 80)

        health = await rag_service.health_check()

        print("\nHealth Status:")
        for service, status in health.items():
            emoji = "✓" if status is True else "✗" if status is False else "⊝"
            print(f"  {emoji} {service}: {status}")

        # Statistics
        print("\n" + "="*80)
        print("Getting statistics...")
        print("-" * 80)

        stats = await rag_service.get_stats()

        print("\nRAG Service Stats:")
        print(f"  Model: {stats.get('model', 'N/A')}")
        print(f"  Cache enabled: {stats.get('use_cache', False)}")
        print(f"  Rerank enabled: {stats.get('use_rerank', False)}")

        if "cache" in stats and stats["cache"]:
            print("\n  Cache:")
            for key, value in stats["cache"].items():
                print(f"    - {key}: {value}")

        if "retrieval" in stats and stats["retrieval"]:
            print("\n  Retrieval:")
            for key, value in stats["retrieval"].items():
                print(f"    - {key}: {value}")

    finally:
        await rag_service.close()


async def example_custom_prompts():
    """Example: Using custom system prompts and templates."""
    print("\n" + "="*80)
    print("CUSTOM PROMPTS EXAMPLE")
    print("="*80 + "\n")

    # Initialize services
    ollama_service = OllamaService()
    retrieval_service = RetrievalService(ollama_service=ollama_service)
    rerank_service = RerankService()
    stream_service = StreamService()
    cache_service = CacheService()

    # Custom system prompt
    custom_system = """You are a friendly AI tutor specializing in explaining technical concepts.
Always provide clear, beginner-friendly explanations with examples."""

    # Custom prompt template
    custom_template = """Here's what I found in my knowledge base:

{context}

Based on this information, please answer the following question:
{question}

Please explain in simple terms:"""

    rag_service = RAGServiceV2(
        cache_service=cache_service,
        ollama_service=ollama_service,
        retrieval_service=retrieval_service,
        rerank_service=rerank_service,
        stream_service=stream_service,
        system_prompt=custom_system,
        prompt_template=custom_template,
        use_cache=False,
    )

    try:
        print("Query with custom prompts: What is a neural network?")
        print("-" * 80)

        response = await rag_service.query(
            question="What is a neural network?",
            k=3,
            stream=False,
        )

        print(f"\nResponse: {response['response'][:300]}...")
        print(f"\nMetadata: {response['metadata']}")

    finally:
        await rag_service.close()


async def main():
    """Run all examples."""
    print("\n" + "="*80)
    print("RAG SERVICE V2 - COMPREHENSIVE EXAMPLES")
    print("="*80)

    # Example 1: Non-streaming
    await example_non_streaming()

    # Example 2: Streaming
    # await example_streaming()  # Uncomment to run

    # Example 3: Health and stats
    await example_health_and_stats()

    # Example 4: Custom prompts
    # await example_custom_prompts()  # Uncomment to run

    print("\n" + "="*80)
    print("ALL EXAMPLES COMPLETED")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
