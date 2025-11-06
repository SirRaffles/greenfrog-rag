"""
Test script for RetrievalService
Tests hybrid search functionality with ChromaDB and Ollama
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.retrieval_service import RetrievalService
from app.services.ollama_service import OllamaService
import structlog

# Setup basic logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger(__name__)


async def test_retrieval_service():
    """Test retrieval service functionality."""
    print("\n" + "="*60)
    print("GreenFrog RAG - Retrieval Service Test")
    print("="*60 + "\n")

    # Initialize services
    print("1. Initializing services...")
    ollama_service = OllamaService(
        base_url="http://192.168.50.171:11434",
        model="phi3:mini"
    )

    retrieval_service = RetrievalService(
        chromadb_url="http://192.168.50.171:8001",
        ollama_service=ollama_service,
        collection_name="greenfrog"
    )

    try:
        # Health check
        print("\n2. Running health checks...")
        ollama_healthy = await ollama_service.health_check()
        print(f"   Ollama: {'✓ Healthy' if ollama_healthy else '✗ Unhealthy'}")

        retrieval_healthy = await retrieval_service.health_check()
        print(f"   Retrieval: {'✓ Healthy' if retrieval_healthy else '✗ Unhealthy'}")

        if not ollama_healthy or not retrieval_healthy:
            print("\n✗ Services not healthy. Exiting.")
            return

        # Get collection info
        print("\n3. Getting collection info...")
        collection_info = await retrieval_service.get_collection_info()
        print(f"   Collection: {collection_info.get('name', 'N/A')}")

        # Load documents
        print("\n4. Loading documents from ChromaDB...")
        doc_count = await retrieval_service.load_documents()
        print(f"   Loaded {doc_count} documents")

        # Test queries
        test_queries = [
            "What is sustainability?",
            "carbon emissions reduction strategies",
            "renewable energy sources"
        ]

        for i, query in enumerate(test_queries, 1):
            print(f"\n{4 + i}. Testing hybrid search: '{query}'")

            # Hybrid search
            print("   Running hybrid search...")
            results = await retrieval_service.hybrid_search(
                query=query,
                k=5
            )

            print(f"   Found {len(results)} results:")
            for j, result in enumerate(results[:3], 1):
                text_preview = result["text"][:100] + "..." if len(result["text"]) > 100 else result["text"]
                print(f"\n   [{j}] RRF Score: {result.get('rrf_score', 0):.4f}")
                print(f"       Semantic: {result.get('semantic_score', 'N/A')}")
                print(f"       BM25: {result.get('bm25_score', 'N/A')}")
                print(f"       Text: {text_preview}")
                if result.get("metadata"):
                    print(f"       Metadata: {result['metadata']}")

        # Compare search methods
        print("\n" + "="*60)
        print("Comparing search methods...")
        print("="*60)

        comparison_query = "sustainable energy"
        print(f"\nQuery: '{comparison_query}'")

        # Semantic only
        print("\n[Semantic Search]")
        semantic_results = await retrieval_service.semantic_search(
            query=comparison_query,
            k=3
        )
        for j, result in enumerate(semantic_results, 1):
            text_preview = result["text"][:80] + "..." if len(result["text"]) > 80 else result["text"]
            print(f"  {j}. Score: {result.get('score', 0):.4f} - {text_preview}")

        # BM25 only
        print("\n[BM25 Keyword Search]")
        bm25_results = await retrieval_service.keyword_search(
            query=comparison_query,
            k=3
        )
        for j, result in enumerate(bm25_results, 1):
            text_preview = result["text"][:80] + "..." if len(result["text"]) > 80 else result["text"]
            print(f"  {j}. Score: {result.get('score', 0):.4f} - {text_preview}")

        # Hybrid
        print("\n[Hybrid (RRF)]")
        hybrid_results = await retrieval_service.hybrid_search(
            query=comparison_query,
            k=3
        )
        for j, result in enumerate(hybrid_results, 1):
            text_preview = result["text"][:80] + "..." if len(result["text"]) > 80 else result["text"]
            print(f"  {j}. RRF Score: {result.get('rrf_score', 0):.4f} - {text_preview}")

        print("\n" + "="*60)
        print("✓ All tests completed successfully!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n✗ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        print("\nCleaning up...")
        await retrieval_service.close()
        await ollama_service.close()
        print("Done.\n")


if __name__ == "__main__":
    asyncio.run(test_retrieval_service())
