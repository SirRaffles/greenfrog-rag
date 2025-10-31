/**
 * useAvatar Hook
 * Manages avatar video generation and playback
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { avatarAPI, ttsAPI, type AvatarResponse } from '@/lib/api';

interface UseAvatarOptions {
  avatarImage?: string;
  ttsMode?: 'piper' | 'xtts';
  quality?: 'low' | 'medium' | 'high';
  autoPlay?: boolean;
  onError?: (error: Error) => void;
}

interface UseAvatarReturn {
  videoUrl: string | null;
  videoBlob: Blob | null;
  isGenerating: boolean;
  isPlaying: boolean;
  error: string | null;
  progress: string;
  generateFromText: (text: string) => Promise<void>;
  generateFromAudio: (audioBase64: string) => Promise<void>;
  play: () => void;
  pause: () => void;
  reset: () => void;
}

export function useAvatar(options: UseAvatarOptions = {}): UseAvatarReturn {
  const {
    avatarImage = 'greenfrog',
    ttsMode = 'piper',
    quality = 'medium',
    autoPlay = true,
    onError,
  } = options;

  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoBlob, setVideoBlob] = useState<Blob | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<string>('');

  const videoRef = useRef<HTMLVideoElement | null>(null);

  const generateFromText = useCallback(async (text: string) => {
    if (!text.trim()) return;

    setIsGenerating(true);
    setError(null);
    setProgress('Generating speech...');

    try {
      // Step 1: Generate TTS audio
      const ttsResponse = await ttsAPI.synthesize({
        text,
        mode: ttsMode,
      });

      setProgress('Creating avatar video...');

      // Step 2: Generate avatar video with audio
      const response = await avatarAPI.generate({
        audio_base64: ttsResponse.audio_base64,
        avatar_image: avatarImage,
        quality,
      });

      // Convert base64 to blob if provided
      if (response.video_base64) {
        const videoData = atob(response.video_base64);
        const videoArray = new Uint8Array(videoData.length);
        for (let i = 0; i < videoData.length; i++) {
          videoArray[i] = videoData.charCodeAt(i);
        }
        const blob = new Blob([videoArray], { type: 'video/mp4' });
        setVideoBlob(blob);

        const url = URL.createObjectURL(blob);
        setVideoUrl(url);
      }

      setProgress('Avatar ready!');

      // Auto-play if enabled
      if (autoPlay && videoRef.current) {
        setTimeout(() => {
          videoRef.current?.play();
        }, 100);
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate avatar';
      setError(errorMessage);
      setProgress('');

      if (onError) {
        onError(err instanceof Error ? err : new Error(errorMessage));
      }
    } finally {
      setIsGenerating(false);
    }
  }, [avatarImage, quality, ttsMode, autoPlay, onError]);

  const generateFromAudio = useCallback(async (audioBase64: string) => {
    setIsGenerating(true);
    setError(null);
    setProgress('Creating avatar video...');

    try {
      const response = await avatarAPI.generate({
        audio_base64: audioBase64,
        avatar_image: avatarImage,
        quality,
      });

      // Convert base64 to blob
      if (response.video_base64) {
        const videoData = atob(response.video_base64);
        const videoArray = new Uint8Array(videoData.length);
        for (let i = 0; i < videoData.length; i++) {
          videoArray[i] = videoData.charCodeAt(i);
        }
        const blob = new Blob([videoArray], { type: 'video/mp4' });
        setVideoBlob(blob);

        const url = URL.createObjectURL(blob);
        setVideoUrl(url);
      }

      setProgress('Avatar ready!');

      if (autoPlay && videoRef.current) {
        setTimeout(() => {
          videoRef.current?.play();
        }, 100);
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate avatar';
      setError(errorMessage);
      setProgress('');

      if (onError) {
        onError(err instanceof Error ? err : new Error(errorMessage));
      }
    } finally {
      setIsGenerating(false);
    }
  }, [avatarImage, quality, autoPlay, onError]);

  const play = useCallback(() => {
    if (videoRef.current) {
      videoRef.current.play();
      setIsPlaying(true);
    }
  }, []);

  const pause = useCallback(() => {
    if (videoRef.current) {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  }, []);

  const reset = useCallback(() => {
    if (videoUrl) {
      URL.revokeObjectURL(videoUrl);
    }
    setVideoUrl(null);
    setVideoBlob(null);
    setIsPlaying(false);
    setError(null);
    setProgress('');
  }, [videoUrl]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (videoUrl) {
        URL.revokeObjectURL(videoUrl);
      }
    };
  }, [videoUrl]);

  return {
    videoUrl,
    videoBlob,
    isGenerating,
    isPlaying,
    error,
    progress,
    generateFromText,
    generateFromAudio,
    play,
    pause,
    reset,
  };
}

// Helper function to attach video ref
export function useVideoRef() {
  return useRef<HTMLVideoElement>(null);
}
