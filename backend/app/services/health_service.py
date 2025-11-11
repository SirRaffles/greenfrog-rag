"""
Health Check Service
Comprehensive health checks for all system dependencies
"""

import asyncio
from typing import Dict, Any, Optional
import structlog
import httpx
import redis.asyncio as redis
import chromadb
import os
from datetime import datetime

logger = structlog.get_logger(__name__)


class HealthCheckService:
    """
    Centralized health check service for all dependencies.
    """

    def __init__(self):
        self.timeout = 5.0  # 5 second timeout for health checks

    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity."""
        redis_url = os.getenv("REDIS_URL", "redis://greenfrog-redis:6379")

        try:
            r = await redis.from_url(redis_url, socket_timeout=self.timeout)
            await r.ping()
            await r.close()

            return {
                "status": "healthy",
                "url": redis_url.split("@")[-1],  # Hide password if any
                "message": "Redis connection successful"
            }
        except redis.ConnectionError as e:
            logger.error("redis_health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": "Connection failed",
                "message": str(e)
            }
        except asyncio.TimeoutError:
            return {
                "status": "unhealthy",
                "error": "Timeout",
                "message": f"Redis did not respond within {self.timeout}s"
            }
        except Exception as e:
            logger.error("redis_health_check_error", error=str(e))
            return {
                "status": "unhealthy",
                "error": type(e).__name__,
                "message": str(e)
            }

    async def check_chromadb(self) -> Dict[str, Any]:
        """Check ChromaDB connectivity."""
        chromadb_url = os.getenv("CHROMADB_URL", "http://chromadb:8000")

        try:
            # Parse URL to get host and port
            url_parts = chromadb_url.replace("http://", "").replace("https://", "").split(":")
            host = url_parts[0]
            port = int(url_parts[1]) if len(url_parts) > 1 else 8000

            # Create client and check heartbeat
            client = chromadb.HttpClient(host=host, port=port)
            heartbeat = client.heartbeat()

            if heartbeat:
                # Try to get collections as additional check
                try:
                    collections = client.list_collections()
                    collection_count = len(collections)
                except:
                    collection_count = "unknown"

                return {
                    "status": "healthy",
                    "url": f"{host}:{port}",
                    "collections": collection_count,
                    "message": "ChromaDB connection successful"
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": "Heartbeat failed",
                    "message": "ChromaDB did not respond to heartbeat"
                }

        except Exception as e:
            logger.error("chromadb_health_check_error", error=str(e))
            return {
                "status": "unhealthy",
                "error": type(e).__name__,
                "message": str(e)
            }

    async def check_ollama(self) -> Dict[str, Any]:
        """Check Ollama service connectivity."""
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Try to list models
                response = await client.get(f"{ollama_url}/api/tags")

                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    model_names = [m.get("name", "unknown") for m in models]

                    return {
                        "status": "healthy",
                        "url": ollama_url.split("://")[-1],
                        "models": model_names,
                        "model_count": len(models),
                        "message": "Ollama connection successful"
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status_code}",
                        "message": "Ollama responded with error"
                    }

        except httpx.ConnectError as e:
            logger.error("ollama_health_check_connection_failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": "Connection failed",
                "message": f"Cannot reach Ollama at {ollama_url}"
            }
        except asyncio.TimeoutError:
            return {
                "status": "unhealthy",
                "error": "Timeout",
                "message": f"Ollama did not respond within {self.timeout}s"
            }
        except Exception as e:
            logger.error("ollama_health_check_error", error=str(e))
            return {
                "status": "unhealthy",
                "error": type(e).__name__,
                "message": str(e)
            }

    async def check_anythingllm(self) -> Dict[str, Any]:
        """Check AnythingLLM service connectivity."""
        anythingllm_url = os.getenv("ANYTHINGLLM_URL", "http://anythingllm:3001")
        api_key = os.getenv("ANYTHINGLLM_API_KEY", "")

        if not api_key:
            return {
                "status": "disabled",
                "message": "AnythingLLM API key not configured"
            }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Try to get workspaces
                response = await client.get(
                    f"{anythingllm_url}/api/v1/workspaces",
                    headers={"Authorization": f"Bearer {api_key}"}
                )

                if response.status_code == 200:
                    data = response.json()
                    workspaces = data.get("workspaces", [])

                    return {
                        "status": "healthy",
                        "url": anythingllm_url.split("://")[-1],
                        "workspaces": len(workspaces),
                        "message": "AnythingLLM connection successful"
                    }
                elif response.status_code == 401:
                    return {
                        "status": "unhealthy",
                        "error": "Authentication failed",
                        "message": "Invalid API key"
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status_code}",
                        "message": "AnythingLLM responded with error"
                    }

        except httpx.ConnectError as e:
            logger.error("anythingllm_health_check_connection_failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": "Connection failed",
                "message": f"Cannot reach AnythingLLM at {anythingllm_url}"
            }
        except asyncio.TimeoutError:
            return {
                "status": "unhealthy",
                "error": "Timeout",
                "message": f"AnythingLLM did not respond within {self.timeout}s"
            }
        except Exception as e:
            logger.error("anythingllm_health_check_error", error=str(e))
            return {
                "status": "unhealthy",
                "error": type(e).__name__,
                "message": str(e)
            }

    async def check_tts(self) -> Dict[str, Any]:
        """Check TTS service (Piper or XTTS) connectivity."""
        tts_mode = os.getenv("TTS_MODE", "piper")

        if tts_mode == "piper":
            piper_url = os.getenv("PIPER_URL", "http://piper-tts:5000")

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(f"{piper_url}/health")

                    if response.status_code == 200:
                        return {
                            "status": "healthy",
                            "mode": "piper",
                            "url": piper_url.split("://")[-1],
                            "message": "Piper TTS connection successful"
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "mode": "piper",
                            "error": f"HTTP {response.status_code}",
                            "message": "Piper TTS responded with error"
                        }

            except Exception as e:
                logger.error("piper_health_check_error", error=str(e))
                return {
                    "status": "unhealthy",
                    "mode": "piper",
                    "error": type(e).__name__,
                    "message": str(e)
                }

        elif tts_mode == "xtts":
            xtts_url = os.getenv("XTTS_URL", "http://xtts-v2:5001")

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(f"{xtts_url}/health")

                    if response.status_code == 200:
                        return {
                            "status": "healthy",
                            "mode": "xtts",
                            "url": xtts_url.split("://")[-1],
                            "message": "XTTS-v2 connection successful"
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "mode": "xtts",
                            "error": f"HTTP {response.status_code}",
                            "message": "XTTS-v2 responded with error"
                        }

            except Exception as e:
                logger.error("xtts_health_check_error", error=str(e))
                return {
                    "status": "unhealthy",
                    "mode": "xtts",
                    "error": type(e).__name__,
                    "message": str(e)
                }

        else:
            return {
                "status": "unknown",
                "mode": tts_mode,
                "message": f"Unknown TTS mode: {tts_mode}"
            }

    async def check_all(self) -> Dict[str, Any]:
        """
        Run all health checks in parallel and return comprehensive status.
        """
        logger.info("running_comprehensive_health_check")

        start_time = datetime.utcnow()

        # Run all checks in parallel
        results = await asyncio.gather(
            self.check_redis(),
            self.check_chromadb(),
            self.check_ollama(),
            self.check_anythingllm(),
            self.check_tts(),
            return_exceptions=True
        )

        redis_health, chromadb_health, ollama_health, anythingllm_health, tts_health = results

        # Handle any exceptions
        def handle_result(result, service_name):
            if isinstance(result, Exception):
                logger.error(f"{service_name}_health_check_exception", error=str(result))
                return {
                    "status": "unhealthy",
                    "error": "Exception",
                    "message": str(result)
                }
            return result

        redis_health = handle_result(redis_health, "redis")
        chromadb_health = handle_result(chromadb_health, "chromadb")
        ollama_health = handle_result(ollama_health, "ollama")
        anythingllm_health = handle_result(anythingllm_health, "anythingllm")
        tts_health = handle_result(tts_health, "tts")

        # Determine overall status
        critical_services = [redis_health, chromadb_health, ollama_health]
        all_critical_healthy = all(s["status"] == "healthy" for s in critical_services)

        overall_status = "healthy" if all_critical_healthy else "degraded"

        # If any critical service is unhealthy, status is unhealthy
        if any(s["status"] == "unhealthy" for s in critical_services):
            overall_status = "unhealthy"

        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        response = {
            "status": overall_status,
            "timestamp": start_time.isoformat(),
            "duration_ms": round(duration_ms, 2),
            "services": {
                "redis": redis_health,
                "chromadb": chromadb_health,
                "ollama": ollama_health,
                "anythingllm": anythingllm_health,
                "tts": tts_health
            },
            "features": {
                "rag_v2": os.getenv("USE_RAG_V2", "true").lower() == "true",
                "cache": os.getenv("USE_CACHE", "true").lower() == "true",
                "rerank": os.getenv("USE_RERANK", "true").lower() == "true"
            }
        }

        logger.info(
            "health_check_complete",
            status=overall_status,
            duration_ms=round(duration_ms, 2)
        )

        return response


# Global instance
_health_service: Optional[HealthCheckService] = None


def get_health_service() -> HealthCheckService:
    """Get or create health service singleton."""
    global _health_service
    if _health_service is None:
        _health_service = HealthCheckService()
    return _health_service
