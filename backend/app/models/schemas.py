"""
Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# Chat Schemas
# ============================================================================

class ChatMessage(BaseModel):
    """Single chat message"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    """Chat request payload"""
    message: str = Field(..., description="User message", min_length=1)
    workspace_slug: str = Field(default="greenfrog", description="AnythingLLM workspace slug")
    mode: str = Field(default="chat", description="Chat mode: 'chat' or 'query'")
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=1024, ge=1, le=4096)
    session_id: Optional[str] = Field(default=None, description="Session ID for context")


class ChatResponse(BaseModel):
    """Chat response payload"""
    response: str = Field(..., description="Assistant response")
    sources: Optional[List[Dict[str, Any]]] = Field(default=[], description="RAG sources used")
    session_id: str = Field(..., description="Session ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    model: Optional[str] = Field(default=None, description="Model used")


# ============================================================================
# TTS Schemas
# ============================================================================

class TTSRequest(BaseModel):
    """Text-to-speech request"""
    text: str = Field(..., description="Text to convert to speech", min_length=1, max_length=5000)
    mode: str = Field(default="piper", description="TTS mode: 'piper' or 'xtts'")
    voice: Optional[str] = Field(default="en_US-lessac-medium", description="Voice model")
    speed: Optional[float] = Field(default=1.0, ge=0.5, le=2.0, description="Speech speed")
    language: Optional[str] = Field(default="en", description="Language code")


class TTSResponse(BaseModel):
    """Text-to-speech response"""
    audio_url: str = Field(..., description="URL to generated audio file")
    audio_base64: Optional[str] = Field(default=None, description="Base64 encoded audio")
    duration: Optional[float] = Field(default=None, description="Audio duration in seconds")
    mode_used: str = Field(..., description="TTS mode used")
    text_length: int = Field(..., description="Input text length")


# ============================================================================
# Avatar Schemas
# ============================================================================

class AvatarRequest(BaseModel):
    """Avatar generation request"""
    audio_url: Optional[str] = Field(default=None, description="URL to audio file")
    audio_base64: Optional[str] = Field(default=None, description="Base64 encoded audio")
    text: Optional[str] = Field(default=None, description="Text to generate TTS first")
    avatar_image: Optional[str] = Field(default="greenfrog", description="Avatar image identifier")
    quality: str = Field(default="medium", description="Quality: 'low', 'medium', 'high'")


class AvatarResponse(BaseModel):
    """Avatar generation response"""
    video_url: str = Field(..., description="URL to generated avatar video")
    video_base64: Optional[str] = Field(default=None, description="Base64 encoded video")
    duration: Optional[float] = Field(default=None, description="Video duration in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Scraper Schemas
# ============================================================================

class ScraperRequest(BaseModel):
    """Web scraping request"""
    url: str = Field(..., description="URL to scrape")
    engine: Optional[str] = Field(default=None, description="Preferred engine: 'crawl4ai', 'read_fast', 'puppeteer'")
    use_fallback: bool = Field(default=True, description="Enable fallback to other engines")


class ScraperBulkRequest(BaseModel):
    """Bulk web scraping request"""
    urls: List[str] = Field(..., description="List of URLs to scrape", min_items=1, max_items=100)
    max_concurrent: int = Field(default=5, ge=1, le=20, description="Max concurrent requests")
    engine: Optional[str] = Field(default=None, description="Preferred engine for all URLs")


class ScraperResponse(BaseModel):
    """Web scraping response"""
    url: str = Field(..., description="URL scraped")
    title: str = Field(..., description="Page title")
    content: str = Field(..., description="Extracted content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    engine_used: str = Field(..., description="Scraping engine used")
    success: bool = Field(..., description="Scraping success status")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Health Check Schemas
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Overall health status")
    services: Dict[str, str] = Field(..., description="Individual service statuses")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response"""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(default=None, description="Error code")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
