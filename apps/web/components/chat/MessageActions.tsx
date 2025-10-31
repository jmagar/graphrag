"use client";

import { useState } from 'react';

interface MessageActionsProps {
  timestamp: string;
  onCopy?: () => void;
  onRegenerate?: () => void;
  reactions?: number;
}

export function MessageActions({ timestamp, onCopy, onRegenerate, reactions = 2 }: MessageActionsProps) {
  const [reacted, setReacted] = useState(false);

  return (
    <div className="flex items-center gap-2 pt-1">
      <button
        type="button"
        onClick={() => setReacted(!reacted)}
        aria-label={reacted ? `Remove reaction (${reactions} reactions)` : `Add reaction (${reactions} reactions)`}
        aria-pressed={reacted}
        className={`reaction-btn flex items-center gap-1 px-3 py-2 min-w-[44px] min-h-[44px] md:px-2 md:py-1 md:min-w-0 md:min-h-0 rounded-md hover:bg-blue-50 dark:hover:bg-blue-500/10 text-xs text-zinc-500 hover:text-blue-600 dark:hover:text-blue-400 border border-transparent hover:border-blue-200 dark:hover:border-blue-500/20 transition-all ${reacted ? 'bg-blue-50 dark:bg-blue-500/10' : ''}`}
      >
        <span className="text-sm" aria-hidden="true">👍</span>
        <span className="font-medium text-xs" aria-live="polite">{reactions}</span>
      </button>
      <button
        type="button"
        onClick={onCopy}
        aria-label="Copy message to clipboard"
        className="p-2 min-w-[44px] min-h-[44px] md:p-1 md:min-w-0 md:min-h-0 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-md text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
        title="Copy message"
      >
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
        </svg>
      </button>
      {onRegenerate && (
        <button
          type="button"
          onClick={onRegenerate}
          aria-label="Regenerate response"
          className="p-2 min-w-[44px] min-h-[44px] md:p-1 md:min-w-0 md:min-h-0 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-md text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
          title="Regenerate response"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
        </button>
      )}
      <div className="text-xs text-zinc-400 opacity-0 group-hover:opacity-100 ml-auto">{timestamp}</div>
    </div>
  );
}
