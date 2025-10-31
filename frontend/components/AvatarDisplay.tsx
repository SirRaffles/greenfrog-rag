/**
 * AvatarDisplay Component
 * Displays the GreenFrog talking avatar video
 */

'use client';

import { useEffect, useRef } from 'react';
import { Loader2 } from 'lucide-react';

interface AvatarDisplayProps {
  videoUrl: string | null;
  isGenerating: boolean;
  isPlaying: boolean;
  progress: string;
  onVideoEnd?: () => void;
  onVideoPlay?: () => void;
  onVideoPause?: () => void;
}

export function AvatarDisplay({
  videoUrl,
  isGenerating,
  isPlaying,
  progress,
  onVideoEnd,
  onVideoPlay,
  onVideoPause,
}: AvatarDisplayProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleEnded = () => {
      onVideoEnd?.();
    };

    const handlePlay = () => {
      onVideoPlay?.();
    };

    const handlePause = () => {
      onVideoPause?.();
    };

    video.addEventListener('ended', handleEnded);
    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);

    return () => {
      video.removeEventListener('ended', handleEnded);
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
    };
  }, [onVideoEnd, onVideoPlay, onVideoPause]);

  return (
    <div className="relative w-full max-w-md mx-auto">
      <div className="aspect-square rounded-2xl overflow-hidden bg-gradient-sustainability shadow-2xl border-4 border-primary-400">
        {/* Video display */}
        {videoUrl && !isGenerating ? (
          <video
            ref={videoRef}
            src={videoUrl}
            className="w-full h-full object-cover"
            autoPlay
            playsInline
            controls={false}
          />
        ) : (
          // Placeholder when no video
          <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-br from-primary-500 to-primary-700 text-white">
            {isGenerating ? (
              <>
                <Loader2 className="w-16 h-16 animate-spin mb-4" />
                <p className="text-lg font-medium">{progress}</p>
                <p className="text-sm opacity-75 mt-2">
                  Generating avatar video...
                </p>
              </>
            ) : (
              <>
                <div className="w-32 h-32 rounded-full bg-white/20 flex items-center justify-center mb-4 avatar-pulse">
                  <span className="text-6xl">🐸</span>
                </div>
                <p className="text-xl font-bold">GreenFrog</p>
                <p className="text-sm opacity-75 mt-2">
                  Ask me about sustainability!
                </p>
              </>
            )}
          </div>
        )}
      </div>

      {/* Status indicator */}
      {isPlaying && (
        <div className="absolute top-4 right-4 bg-red-500 text-white px-3 py-1 rounded-full text-xs font-medium flex items-center gap-2">
          <span className="w-2 h-2 bg-white rounded-full animate-pulse"></span>
          Speaking
        </div>
      )}
    </div>
  );
}
