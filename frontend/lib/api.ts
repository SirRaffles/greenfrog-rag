/**
 * API Client Library for GreenFrog RAG Backend
 * Provides type-safe interfaces for all backend endpoints
 */

import axios, { AxiosInstance, AxiosError } from 'axios';

// ============================================================================
// Configuration
// ============================================================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance with default config
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutes for LLM generation
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging and auth
apiClient.interceptors.request.use(
  (config) => {
    // Add API key if available (future-ready)
    const apiKey = process.env.NEXT_PUBLIC_API_KEY;
    if (apiKey) {
      config.headers['X-API-Key'] = apiKey;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Enhanced error handling
    if (error.response) {
      // Server responded with error
      const message = (error.response.data as any)?.detail || error.message;
      throw new Error(`API Error: ${message}`);
    } else if (error.request) {
      // Request made but no response
      throw new Error('No response from server. Please check your connection.');
    } else {
      // Request setup error
      throw new Error(`Request error: ${error.message}`);
    }
  }
);

// ============================================================================
// Type Definitions
// ============================================================================

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export interface ChatSource {
  id: string;
  text: string;
  score: number;
  metadata: Record<string, any>;
  method?: string;
}

export interface ChatResponse {
  response: string;
  sources: ChatSource[];
  session_id: string;
  timestamp: string;
  model?: string;
  metadata?: {
    cached?: boolean;
    retrieval_method?: string;
    retrieval_time_ms?: number;
    generation_time_ms?: number;
    total_time_ms?: number;
    [key: string]: any;
  };
}

export interface ChatRequest {
  message: string;
  workspace_slug?: string;
  mode?: 'chat' | 'query';
  session_id?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface ChatV2Request {
  question: string;
  workspace?: string;
  k?: number;
  temperature?: number;
  max_tokens?: number;
  min_score?: number;
  model?: string;
}

export interface TTSRequest {
  text: string;
  mode?: 'piper' | 'xtts';
  voice?: string;
  speed?: number;
}

export interface TTSResponse {
  audio_base64: string;
  mode: string;
  duration?: number;
  format?: string;
}

export interface AvatarRequest {
  audio_base64: string;
  avatar_image?: string;
  quality?: 'low' | 'medium' | 'high';
  pose_style?: string;
  expression_scale?: number;
}

export interface AvatarResponse {
  video_base64: string;
  duration?: number;
  format?: string;
  frames?: number;
}

export interface HealthResponse {
  status: string;
  checks?: Record<string, any>;
  timestamp?: string;
}

export interface WorkspaceInfo {
  id: string;
  name: string;
  slug: string;
  documents: number;
  description?: string;
}

// ============================================================================
// Chat API (V1 - Legacy)
// ============================================================================

export const chatAPI = {
  /**
   * Send a message to the chat endpoint (V1 API)
   */
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await apiClient.post<ChatResponse>('/api/chat/message', {
      message: request.message,
      workspace_slug: request.workspace_slug || 'greenfrog',
      mode: request.mode || 'chat',
      session_id: request.session_id,
      temperature: request.temperature,
      max_tokens: request.max_tokens,
    });
    return response.data;
  },

  /**
   * Send a single query (no session/history)
   */
  async query(message: string, workspace?: string): Promise<ChatResponse> {
    const response = await apiClient.post<ChatResponse>('/api/chat/query', {
      message,
      workspace_slug: workspace || 'greenfrog',
    });
    return response.data;
  },

  /**
   * Get available workspaces
   */
  async getWorkspaces(): Promise<WorkspaceInfo[]> {
    const response = await apiClient.get<WorkspaceInfo[]>('/api/chat/workspaces');
    return response.data;
  },

  /**
   * Get workspace statistics
   */
  async getWorkspaceStats(workspace: string): Promise<any> {
    const response = await apiClient.get(`/api/chat/workspace/${workspace}/stats`);
    return response.data;
  },
};

// ============================================================================
// Chat API V2 (Advanced RAG)
// ============================================================================

export const chatV2API = {
  /**
   * Send a query to RAG V2 (non-streaming)
   */
  async query(request: ChatV2Request): Promise<ChatResponse> {
    const response = await apiClient.post<ChatResponse>('/api/v2/chat/query', {
      question: request.question,
      workspace: request.workspace || 'greenfrog',
      k: request.k || 5,
      temperature: request.temperature || 0.7,
      max_tokens: request.max_tokens || 1024,
      min_score: request.min_score || 0.0,
      model: request.model,
    });
    return response.data;
  },

  /**
   * Stream a query response (Server-Sent Events)
   * Returns an EventSource for streaming
   */
  createStreamEventSource(request: ChatV2Request): EventSource {
    // Build query params
    const params = new URLSearchParams({
      question: request.question,
      workspace: request.workspace || 'greenfrog',
      k: String(request.k || 5),
      temperature: String(request.temperature || 0.7),
      max_tokens: String(request.max_tokens || 1024),
      min_score: String(request.min_score || 0.0),
    });

    if (request.model) {
      params.append('model', request.model);
    }

    const url = `${API_BASE_URL}/api/v2/chat/stream?${params.toString()}`;
    return new EventSource(url);
  },

  /**
   * Get health status of V2 services
   */
  async health(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>('/api/v2/chat/health');
    return response.data;
  },

  /**
   * Get V2 statistics
   */
  async stats(): Promise<any> {
    const response = await apiClient.get('/api/v2/chat/stats');
    return response.data;
  },

  /**
   * Invalidate cache entries
   */
  async invalidateCache(workspace?: string): Promise<{ deleted: number }> {
    const response = await apiClient.post('/api/v2/chat/cache/invalidate', {
      workspace: workspace || 'greenfrog',
    });
    return response.data;
  },
};

// ============================================================================
// TTS API
// ============================================================================

export const ttsAPI = {
  /**
   * Synthesize text to speech
   */
  async synthesize(request: TTSRequest): Promise<TTSResponse> {
    const response = await apiClient.post<TTSResponse>('/api/tts/synthesize', {
      text: request.text,
      mode: request.mode || 'piper',
      voice: request.voice,
      speed: request.speed || 1.0,
    });
    return response.data;
  },

  /**
   * Get available voices
   */
  async getVoices(mode: 'piper' | 'xtts' = 'piper'): Promise<string[]> {
    const response = await apiClient.get<string[]>(`/api/tts/voices?mode=${mode}`);
    return response.data;
  },

  /**
   * Get TTS health status
   */
  async health(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>('/api/tts/health');
    return response.data;
  },
};

// ============================================================================
// Avatar API
// ============================================================================

export const avatarAPI = {
  /**
   * Generate avatar video from audio
   */
  async generate(request: AvatarRequest): Promise<AvatarResponse> {
    const response = await apiClient.post<AvatarResponse>(
      '/api/avatar/generate',
      {
        audio_base64: request.audio_base64,
        avatar_image: request.avatar_image || 'greenfrog',
        quality: request.quality || 'medium',
        pose_style: request.pose_style,
        expression_scale: request.expression_scale || 1.0,
      },
      {
        timeout: 180000, // 3 minutes for video generation
      }
    );
    return response.data;
  },

  /**
   * Get avatar health status
   */
  async health(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>('/api/avatar/health');
    return response.data;
  },
};

// ============================================================================
// Retrieval API
// ============================================================================

export const retrievalAPI = {
  /**
   * Search documents
   */
  async search(query: string, k: number = 10, method: 'hybrid' | 'semantic' | 'keyword' = 'hybrid'): Promise<ChatSource[]> {
    const response = await apiClient.post<ChatSource[]>('/api/retrieval/search', {
      query,
      k,
      method,
    });
    return response.data;
  },

  /**
   * Get retrieval service health
   */
  async health(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>('/api/retrieval/health');
    return response.data;
  },
};

// ============================================================================
// Scraper API
// ============================================================================

export const scraperAPI = {
  /**
   * Scrape a single URL
   */
  async scrapeUrl(url: string): Promise<{ content: string; metadata: any }> {
    const response = await apiClient.post('/api/scraper/scrape', { url });
    return response.data;
  },

  /**
   * Scrape multiple URLs
   */
  async scrapeBulk(urls: string[]): Promise<Array<{ url: string; content: string; metadata: any }>> {
    const response = await apiClient.post('/api/scraper/scrape-bulk', { urls });
    return response.data;
  },
};

// ============================================================================
// System API
// ============================================================================

export const systemAPI = {
  /**
   * Get overall system health
   */
  async health(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>('/health');
    return response.data;
  },

  /**
   * Get system information
   */
  async info(): Promise<any> {
    const response = await apiClient.get('/');
    return response.data;
  },
};

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Convert base64 string to Blob
 */
export function base64ToBlob(base64: string, mimeType: string = 'video/mp4'): Blob {
  const byteCharacters = atob(base64);
  const byteArray = new Uint8Array(byteCharacters.length);

  for (let i = 0; i < byteCharacters.length; i++) {
    byteArray[i] = byteCharacters.charCodeAt(i);
  }

  return new Blob([byteArray], { type: mimeType });
}

/**
 * Create object URL from base64 string
 */
export function base64ToObjectURL(base64: string, mimeType: string = 'video/mp4'): string {
  const blob = base64ToBlob(base64, mimeType);
  return URL.createObjectURL(blob);
}

/**
 * Test API connectivity
 */
export async function testConnection(): Promise<boolean> {
  try {
    await systemAPI.health();
    return true;
  } catch (error) {
    console.error('API connection test failed:', error);
    return false;
  }
}

// ============================================================================
// Export axios instance for advanced usage
// ============================================================================

export { apiClient };
export default apiClient;
