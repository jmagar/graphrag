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

  const getStatusBadge = () => {
    if (status === 'running') {
      return (
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
          <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
          <span className="text-[10px] font-medium text-blue-700 dark:text-blue-400">Running</span>
        </div>
      );
    }

    if (status === 'complete') {
      return (
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
          <svg className="w-2.5 h-2.5 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7"/>
          </svg>
          <span className="text-[10px] font-medium text-green-700 dark:text-green-400">Done</span>
        </div>
      );
    }

    if (status === 'error') {
      return (
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
          <svg className="w-2.5 h-2.5 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M6 18L18 6M6 6l12 12"/>
          </svg>
          <span className="text-[10px] font-medium text-red-700 dark:text-red-400">Failed</span>
        </div>
      );
    }

    return null;
  };

  return (
    <div className="inline-flex flex-col bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg overflow-hidden">
      <button
        onClick={() => args && setExpanded(!expanded)}
        className="flex items-center gap-2 px-3 py-2 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors"
      >
        {/* Icon */}
        <div className="flex items-center justify-center w-6 h-6 rounded bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400">
          {getToolIcon()}
        </div>

        {/* Tool name */}
        <span className="text-xs font-medium text-zinc-900 dark:text-zinc-100">
          {cleanName}
        </span>

        {/* Status badge */}
        <div className="ml-auto flex items-center gap-2">
          {getStatusBadge()}

          {/* Expand arrow */}
          {args && (
            <svg
              className={`w-3 h-3 text-zinc-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"/>
            </svg>
          )}
        </div>
      </button>

      {/* Expanded args */}
      {expanded && args && (
        <div className="px-3 py-2 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/50">
          <pre className="text-[10px] text-zinc-600 dark:text-zinc-400 font-mono whitespace-pre-wrap break-words">
            {args}
          </pre>
        </div>
      )}
    </div>
  );
}
