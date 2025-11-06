"""
Foundation Services Integration Test
Tests cache_service.py and ollama_service.py integration
"""

import asyncio
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.services.cache_service import CacheService
from app.services.ollama_service import OllamaService


async def test_redis_connection():
    """Test Redis connectivity."""
    print("\n=== Testing Redis Connection ===")
    cache = CacheService(
        redis_url="redis://192.168.50.171:6400",
        similarity_threshold=0.95,
        ttl_seconds=3600
    )

    try:
        is_healthy = await cache.health_check()
        if is_healthy:
            print("✅ Redis connection: OK")
            return True
        else:
            print("❌ Redis connection: FAILED")
            return False
    except Exception as e:
        print(f"❌ Redis connection error: {e}")
        return False
    finally:
        await cache.close()


async def test_ollama_connection():
    """Test Ollama connectivity."""
    print("\n=== Testing Ollama Connection ===")
    ollama = OllamaService(
        base_url="http://192.168.50.171:11434",
        model="phi3:mini",
        timeout=60.0
    )

    try:
        is_healthy = await ollama.health_check()
        if is_healthy:
            print("✅ Ollama connection: OK")

            # List available models
            models = await ollama.list_models()
            print(f"✅ Available models: {len(models)}")
            for model in models:
                print(f"  - {model.get('name', 'unknown')}")
            return True
        else:
            print("❌ Ollama connection: FAILED")
            return False
    except Exception as e:
        print(f"❌ Ollama connection error: {e}")
        return False
    finally:
        await ollama.close()


async def test_cache_operations():
    """Test cache set/get operations."""
    print("\n=== Testing Cache Operations ===")
    cache = CacheService(
        redis_url="redis://192.168.50.171:6400",
        similarity_threshold=0.95,
        ttl_seconds=3600
    )

    try:
        # Test set
        test_query = "What is sustainability?"
        test_response = {
            "response": "Sustainability is the practice of meeting present needs without compromising future generations.",
            "model": "phi3:mini",
            "timestamp": "2025-11-04T00:00:00Z"
        }

        success = await cache.set(test_query, test_response, workspace="test")
        if success:
            print("✅ Cache set: OK")
        else:
            print("❌ Cache set: FAILED")
            return False

        # Test exact match get
        cached = await cache.get(test_query, workspace="test", use_semantic=False)
        if cached and cached["response"] == test_response["response"]:
            print("✅ Cache get (exact match): OK")
        else:
            print("❌ Cache get (exact match): FAILED")
            return False

        # Test semantic similarity get
        similar_query = "What does sustainability mean?"
        cached_semantic = await cache.get(similar_query, workspace="test", use_semantic=True)
        if cached_semantic:
            print(f"✅ Cache get (semantic): OK (found similar query)")
        else:
            print(f"⚠️ Cache get (semantic): No match (similarity < 0.95)")

        # Test cache stats
        stats = await cache.get_stats(workspace="test")
        print(f"✅ Cache stats: {stats}")

        return True

    except Exception as e:
        print(f"❌ Cache operations error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await cache.close()


async def test_ollama_generation():
    """Test Ollama text generation."""
    print("\n=== Testing Ollama Generation ===")
    ollama = OllamaService(
        base_url="http://192.168.50.171:11434",
        model="phi3:mini",
        timeout=120.0
    )

    try:
        # Test simple generation
        prompt = "What is sustainability in one sentence?"
        print(f"Prompt: {prompt}")
        print("Generating response...")

        import time
        start_time = time.time()

        result = await ollama.generate(
            prompt=prompt,
            temperature=0.7,
            max_tokens=100
        )

        elapsed = time.time() - start_time

        response_text = result.get("response", "")
        if response_text:
            print(f"✅ Generation: OK ({elapsed:.2f}s)")
            print(f"Response: {response_text[:200]}...")
            return result
        else:
            print("❌ Generation: FAILED (empty response)")
            return None

    except Exception as e:
        print(f"❌ Ollama generation error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        await ollama.close()


async def test_integrated_caching():
    """Test integrated cache + Ollama workflow."""
    print("\n=== Testing Integrated Caching Workflow ===")

    cache = CacheService(
        redis_url="redis://192.168.50.171:6400",
        similarity_threshold=0.95,
        ttl_seconds=3600
    )

    ollama = OllamaService(
        base_url="http://192.168.50.171:11434",
        model="phi3:mini",
        timeout=120.0
    )

    try:
        query = "What is the Matcha Initiative?"

        # First request - should miss cache and generate
        print(f"\n1️⃣ First request (cache miss expected)...")
        import time
        start_time = time.time()

        cached = await cache.get(query, workspace="greenfrog", use_semantic=True)
        if cached:
            print(f"⚠️ Unexpected cache hit!")
            response = cached
        else:
            print(f"✅ Cache miss (as expected)")
            print("Generating response from Ollama...")

            result = await ollama.generate(
                prompt=query,
                temperature=0.7,
                max_tokens=200
            )

            response = {
                "response": result.get("response", ""),
                "model": result.get("model", "phi3:mini"),
                "timestamp": "2025-11-04T00:00:00Z"
            }

            # Cache the response
            await cache.set(query, response, workspace="greenfrog")
            print("✅ Response cached")

        first_elapsed = time.time() - start_time
        print(f"⏱️ First request time: {first_elapsed:.2f}s")
        print(f"Response: {response['response'][:200]}...")

        # Second request - should hit cache
        print(f"\n2️⃣ Second request (cache hit expected)...")
        start_time = time.time()

        cached = await cache.get(query, workspace="greenfrog", use_semantic=False)
        if cached:
            print(f"✅ Cache hit!")
            response = cached
        else:
            print(f"❌ Unexpected cache miss!")
            return False

        second_elapsed = time.time() - start_time
        print(f"⏱️ Second request time: {second_elapsed:.2f}s")
        print(f"Response: {response['response'][:200]}...")

        # Calculate speedup
        if second_elapsed > 0:
            speedup = first_elapsed / second_elapsed
            print(f"\n🚀 Cache speedup: {speedup:.1f}x faster")

        return True

    except Exception as e:
        print(f"❌ Integrated test error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await cache.close()
        await ollama.close()


async def main():
    """Run all tests."""
    print("=" * 60)
    print("GreenFrog RAG Foundation Services Integration Test")
    print("=" * 60)

    results = {
        "redis_connection": False,
        "ollama_connection": False,
        "cache_operations": False,
        "ollama_generation": False,
        "integrated_caching": False
    }

    # Test Redis connection
    results["redis_connection"] = await test_redis_connection()

    # Test Ollama connection
    results["ollama_connection"] = await test_ollama_connection()

    # Only proceed if both connections are OK
    if results["redis_connection"] and results["ollama_connection"]:
        # Test cache operations
        results["cache_operations"] = await test_cache_operations()

        # Test Ollama generation
        ollama_result = await test_ollama_generation()
        results["ollama_generation"] = ollama_result is not None

        # Test integrated workflow
        results["integrated_caching"] = await test_integrated_caching()

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests PASSED!")
        print("=" * 60)
        return 0
    else:
        print("❌ Some tests FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
