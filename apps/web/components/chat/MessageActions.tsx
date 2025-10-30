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
        onClick={() => setReacted(!reacted)}
        className={`reaction-btn flex items-center gap-1 px-2 py-1 rounded-md hover:bg-blue-50 dark:hover:bg-blue-500/10 text-xs text-zinc-500 hover:text-blue-600 dark:hover:text-blue-400 border border-transparent hover:border-blue-200 dark:hover:border-blue-500/20 transition-all ${reacted ? 'bg-blue-50 dark:bg-blue-500/10' : ''}`}
      >
        <span className="text-sm">👍</span>
        <span className="font-medium text-xs">{reactions}</span>
      </button>
      <button
        onClick={onCopy}
        className="p-1 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-md text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
        title="Copy"
      >
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
        </svg>
      </button>
      {onRegenerate && (
        <button
          onClick={onRegenerate}
          className="p-1 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-md text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
          title="Regenerate"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
        </button>
      )}
      <div className="text-xs text-zinc-400 opacity-0 group-hover:opacity-100 ml-auto">{timestamp}</div>
    </div>
  );
}
