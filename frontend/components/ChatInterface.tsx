/**
 * ChatInterface Component
 * Main chat interface combining avatar, messages, and input
 */

'use client';

import { useState } from 'react';
import { useChat } from '@/hooks/useChat';
import { useAvatar } from '@/hooks/useAvatar';
import { AvatarDisplay } from './AvatarDisplay';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { SourcesPanel } from './SourcesPanel';
import { Sparkles, Settings } from 'lucide-react';

interface ChatInterfaceProps {
  workspaceSlug?: string;
}

export function ChatInterface({ workspaceSlug = 'greenfrog' }: ChatInterfaceProps) {
  const [showSources, setShowSources] = useState(false);
  const [avatarEnabled, setAvatarEnabled] = useState(true);

  // Chat management
  const {
    messages,
    isLoading: isChatLoading,
    error: chatError,
    sources,
    sendMessage,
    clearMessages,
  } = useChat({ workspaceSlug });

  // Avatar management
  const {
    videoUrl,
    isGenerating: isAvatarGenerating,
    isPlaying: isAvatarPlaying,
    progress: avatarProgress,
    error: avatarError,
    generateFromText,
  } = useAvatar({
    autoPlay: true,
  });

  // Handle sending message
  const handleSendMessage = async (message: string) => {
    // Send to chat (RAG)
    await sendMessage(message);

    // Note: We'll generate avatar for assistant response in useEffect
    // For now, just send the message
  };

  // Generate avatar for last assistant message
  const lastAssistantMessage = messages
    .filter((m) => m.role === 'assistant')
    .slice(-1)[0];

  // Trigger avatar generation when new assistant message arrives
  if (
    avatarEnabled &&
    lastAssistantMessage &&
    !isAvatarGenerating &&
    !videoUrl
  ) {
    generateFromText(lastAssistantMessage.content);
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-sustainability flex items-center justify-center">
              <span className="text-2xl">🐸</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                GreenFrog
                <Sparkles className="w-5 h-5 text-primary-500" />
              </h1>
              <p className="text-sm text-gray-600">
                Sustainability Assistant
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Sources toggle */}
            {sources && sources.length > 0 && (
              <button
                onClick={() => setShowSources(!showSources)}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                {showSources ? 'Hide' : 'Show'} Sources ({sources.length})
              </button>
            )}

            {/* Avatar toggle */}
            <button
              onClick={() => setAvatarEnabled(!avatarEnabled)}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              title={avatarEnabled ? 'Disable avatar' : 'Enable avatar'}
            >
              Avatar: {avatarEnabled ? 'On' : 'Off'}
            </button>

            {/* Clear chat */}
            <button
              onClick={clearMessages}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Clear
            </button>

            {/* Settings */}
            <button className="p-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors">
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left sidebar - Avatar */}
        {avatarEnabled && (
          <div className="w-96 border-r border-gray-200 bg-white p-6 flex flex-col">
            <AvatarDisplay
              videoUrl={videoUrl}
              isGenerating={isAvatarGenerating}
              isPlaying={isAvatarPlaying}
              progress={avatarProgress}
            />

            {avatarError && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-600">{avatarError}</p>
              </div>
            )}

            <div className="mt-6 text-center text-sm text-gray-600">
              <p className="font-medium mb-2">About GreenFrog</p>
              <p className="text-xs">
                Powered by The Matcha Initiative's sustainability database.
                I can help you with suppliers, solutions, and best practices!
              </p>
            </div>
          </div>
        )}

        {/* Center - Chat */}
        <div className="flex-1 flex flex-col">
          <MessageList messages={messages} isLoading={isChatLoading} />

          {chatError && (
            <div className="px-4 pb-2">
              <div className="max-w-4xl mx-auto p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-600">{chatError}</p>
              </div>
            </div>
          )}

          <MessageInput
            onSend={handleSendMessage}
            isLoading={isChatLoading}
            disabled={false}
          />
        </div>

        {/* Right sidebar - Sources */}
        {showSources && sources && sources.length > 0 && (
          <div className="w-96 border-l border-gray-200 bg-white">
            <SourcesPanel sources={sources} />
          </div>
        )}
      </div>
    </div>
  );
}
