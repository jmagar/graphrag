'use client';

import { useState } from 'react';

interface ToolCallProps {
  command: string;
  args?: string;
  status?: 'running' | 'complete' | 'error';
}

export function ToolCall({ command, args, status = 'running' }: ToolCallProps) {
  const [expanded, setExpanded] = useState(false);
  
  // Clean up MCP tool names (remove mcp__firecrawl-tools__ prefix)
  const cleanName = command.replace(/^mcp__.*?__/, '');
  
  // Get icon based on tool type
  const getToolIcon = () => {
    const name = cleanName.toLowerCase();
    
    if (name.includes('scrape') || name === 'scrape_url') {
      return (
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
      );
    }
    
    if (name.includes('crawl') || name === 'start_crawl' || name === 'check_crawl_status') {
      return (
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/>
        </svg>
      );
    }
    
    if (name.includes('search') || name === 'search_web' || name === 'query_knowledge_base') {
      return (
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
        </svg>
      );
    }
    
    if (name.includes('map') || name === 'map_website') {
      return (
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
        </svg>
      );
    }
    
    if (name.includes('extract')) {
      return (
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"/>
        </svg>
      );
    }
    
    // Default
    return (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
      </svg>
    );
  };

  const statusIcon = status === 'running' ? (
    <div className="relative flex items-center justify-center">
      <div className="absolute w-3 h-3 rounded-full bg-emerald-400/30 dark:bg-emerald-400/20 animate-ping" />
      <div className="w-2 h-2 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 dark:from-emerald-400 dark:to-emerald-500 shadow-sm shadow-emerald-500/50" />
    </div>
  ) : status === 'complete' ? (
    <div className="flex items-center justify-center w-5 h-5 rounded-full bg-gradient-to-br from-emerald-400/20 to-emerald-500/20 dark:from-emerald-400/30 dark:to-emerald-500/30">
      <svg className="w-3 h-3 text-emerald-600 dark:text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7"/>
      </svg>
    </div>
  ) : (
    <div className="flex items-center justify-center w-5 h-5 rounded-full bg-gradient-to-br from-red-400/20 to-red-500/20 dark:from-red-400/30 dark:to-red-500/30">
      <svg className="w-3 h-3 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M6 18L18 6M6 6l12 12"/>
      </svg>
    </div>
  );

  return (
    <div className="inline-flex flex-col bg-gradient-to-br from-white via-zinc-50 to-zinc-100/80 dark:from-zinc-800/80 dark:via-zinc-850/60 dark:to-zinc-900/80 backdrop-blur-xl border border-zinc-200/80 dark:border-zinc-700/50 rounded-2xl shadow-lg shadow-zinc-200/50 dark:shadow-zinc-900/50 hover:shadow-xl hover:shadow-zinc-300/60 dark:hover:shadow-zinc-900/70 transition-all duration-300 hover:scale-[1.02] active:scale-[0.98]">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2.5 px-3.5 py-2.5 w-full text-left group"
      >
        {/* Icon container with gradient background */}
        <div className="relative flex items-center justify-center w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500/10 via-purple-500/10 to-pink-500/10 dark:from-blue-400/20 dark:via-purple-400/20 dark:to-pink-400/20 text-blue-600 dark:text-blue-400 group-hover:scale-110 group-hover:rotate-6 transition-all duration-300 shadow-inner">
          <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-blue-500/5 to-transparent dark:from-blue-400/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
          <div className="relative z-10">
            {getToolIcon()}
          </div>
        </div>

        {/* Tool name with better typography */}
        <span className="text-xs font-bold text-transparent bg-clip-text bg-gradient-to-r from-zinc-800 to-zinc-600 dark:from-zinc-100 dark:to-zinc-300 tracking-tight">
          {cleanName}
        </span>

        {/* Status indicator */}
        {status && (
          <div className="ml-auto flex-shrink-0 flex items-center justify-center pl-2">
            {statusIcon}
          </div>
        )}

        {/* Expand arrow */}
        {args && (
          <svg
            className={`w-3.5 h-3.5 ml-1 text-zinc-400 dark:text-zinc-500 transition-all duration-300 group-hover:text-zinc-600 dark:group-hover:text-zinc-300 ${expanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M19 9l-7 7-7-7"/>
          </svg>
        )}
      </button>

      {/* Expanded args section */}
      {expanded && args && (
        <div className="animate-fade-in px-4 py-3 border-t border-zinc-200/80 dark:border-zinc-700/50 bg-gradient-to-br from-zinc-50/90 to-white/90 dark:from-zinc-900/90 dark:to-zinc-800/90 text-[11px] text-zinc-700 dark:text-zinc-300 font-mono leading-relaxed whitespace-pre-wrap break-words rounded-b-2xl backdrop-blur-sm">
          {args}
        </div>
      )}
    </div>
  );
}
