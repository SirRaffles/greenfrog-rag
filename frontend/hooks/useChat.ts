/**
 * useChat Hook
 * Manages chat state and interactions with RAG backend
 */

import { useState, useCallback, useRef } from 'react';
import { chatAPI, type ChatMessage, type ChatResponse } from '@/lib/api';

interface UseChatOptions {
  workspaceSlug?: string;
  mode?: 'chat' | 'query';
  onError?: (error: Error) => void;
}

interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  sessionId: string | null;
  sources: ChatResponse['sources'];
  sendMessage: (message: string) => Promise<void>;
  clearMessages: () => void;
  retryLastMessage: () => Promise<void>;
}

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const {
    workspaceSlug = 'greenfrog',
    mode = 'chat',
    onError,
  } = options;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sources, setSources] = useState<ChatResponse['sources']>([]);

  const lastUserMessageRef = useRef<string>('');

  const sendMessage = useCallback(async (message: string) => {
    if (!message.trim()) return;

    setIsLoading(true);
    setError(null);
    lastUserMessageRef.current = message;

    // Add user message to chat
    const userMessage: ChatMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);

    try {
      // Send to backend
      const response = await chatAPI.sendMessage({
        message,
        workspace_slug: workspaceSlug,
        mode,
        session_id: sessionId || undefined,
      });

      // Add assistant response
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.response,
        timestamp: response.timestamp,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setSessionId(response.session_id);
      setSources(response.sources || []);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to send message';
      setError(errorMessage);

      if (onError) {
        onError(err instanceof Error ? err : new Error(errorMessage));
      }

      // Add error message to chat
      const errorChatMessage: ChatMessage = {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${errorMessage}. Please try again.`,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, errorChatMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [workspaceSlug, mode, sessionId, onError]);

  const retryLastMessage = useCallback(async () => {
    if (lastUserMessageRef.current) {
      await sendMessage(lastUserMessageRef.current);
    }
  }, [sendMessage]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setSources([]);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    sessionId,
    sources,
    sendMessage,
    clearMessages,
    retryLastMessage,
  };
}
