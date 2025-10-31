/**
 * SourcesPanel Component
 * Displays RAG sources used in responses
 */

'use client';

import { ExternalLink, FileText } from 'lucide-react';

interface Source {
  title: string;
  content: string;
  url?: string;
}

interface SourcesPanelProps {
  sources: Source[];
}

export function SourcesPanel({ sources }: SourcesPanelProps) {
  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <div className="h-full flex flex-col">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">
          <FileText className="w-5 h-5" />
          Sources ({sources.length})
        </h2>
        <p className="text-sm text-gray-600 mt-1">
          Information retrieved from The Matcha Initiative
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {sources.map((source, index) => (
          <SourceCard key={index} source={source} index={index} />
        ))}
      </div>
    </div>
  );
}

function SourceCard({ source, index }: { source: Source; index: number }) {
  return (
    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 hover:border-primary-300 transition-colors">
      <div className="flex items-start justify-between gap-2 mb-2">
        <h3 className="font-medium text-gray-800 flex items-center gap-2">
          <span className="w-6 h-6 rounded-full bg-primary-500 text-white text-xs flex items-center justify-center flex-shrink-0">
            {index + 1}
          </span>
          {source.title}
        </h3>

        {source.url && (
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary-600 hover:text-primary-700 transition-colors"
            title="Open source"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        )}
      </div>

      <p className="text-sm text-gray-600 line-clamp-3">
        {source.content}
      </p>
    </div>
  );
}
