'use client';

import { useState, useEffect } from 'react';

interface CrawlProgressProps {
  jobId: string;
  url: string;
  status: string;
  completed: number;
  total: number;
  creditsUsed: number;
  expiresAt?: string;
  recentPages?: Array<{ url: string; status: string }>;
  onCancel?: () => void;
}

export function CrawlProgress({
  jobId,
  url,
  status,
  completed,
  total,
  creditsUsed,
  expiresAt,
  recentPages = [],
  onCancel
}: CrawlProgressProps) {
  const [timeElapsed, setTimeElapsed] = useState(0);
  const [isExpanded, setIsExpanded] = useState(true);

  // Calculate progress percentage
  const progress = total > 0 ? Math.round((completed / total) * 100) : 0;
  const isComplete = status === 'completed' || status === 'failed';
  const isActive = status === 'scraping' || status === 'processing';

  // Time elapsed counter
  useEffect(() => {
    if (!isActive) return;
    
    const interval = setInterval(() => {
      setTimeElapsed(prev => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [isActive]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const getStatusIcon = () => {
    if (status === 'completed') return '✅';
    if (status === 'failed') return '❌';
    return '🔄';
  };

  const getStatusColor = () => {
    if (status === 'completed') return 'text-green-600 dark:text-green-400';
    if (status === 'failed') return 'text-red-600 dark:text-red-400';
    return 'text-blue-600 dark:text-blue-400';
  };

  return (
    <div className="my-4 border border-zinc-200 dark:border-zinc-700 rounded-lg overflow-hidden bg-gradient-to-br from-white to-zinc-50 dark:from-zinc-900 dark:to-zinc-950 shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950/30 dark:to-purple-950/30 border-b border-zinc-200 dark:border-zinc-700">
        <div className="flex items-center gap-3">
          <div className={`text-2xl ${isActive ? 'animate-spin' : ''}`}>
            {getStatusIcon()}
          </div>
          <div>
            <h3 className={`font-semibold ${getStatusColor()}`}>
              Crawl {status === 'completed' ? 'Complete' : status === 'failed' ? 'Failed' : 'In Progress'}
            </h3>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 truncate max-w-md">
              {url}
            </p>
          </div>
        </div>
        
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-2 hover:bg-white/50 dark:hover:bg-black/20 rounded-lg transition-colors"
        >
          <svg 
            className={`w-5 h-5 text-zinc-600 dark:text-zinc-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="p-4 space-y-4">
          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between items-center text-sm">
              <span className="text-zinc-600 dark:text-zinc-400">Progress</span>
              <span className="font-bold text-zinc-900 dark:text-zinc-100">{progress}%</span>
            </div>
            
            <div className="relative h-3 bg-zinc-200 dark:bg-zinc-800 rounded-full overflow-hidden">
              <div
                className="absolute inset-y-0 left-0 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 rounded-full transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              >
                {isActive && (
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" />
                )}
              </div>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-white dark:bg-zinc-800/50 rounded-lg p-3 border border-zinc-200 dark:border-zinc-700">
              <div className="text-xs text-zinc-600 dark:text-zinc-400 mb-1">Pages</div>
              <div className="text-lg font-bold text-zinc-900 dark:text-zinc-100">
                {completed} <span className="text-sm text-zinc-500">/ {total || '...'}</span>
              </div>
            </div>
            
            <div className="bg-white dark:bg-zinc-800/50 rounded-lg p-3 border border-zinc-200 dark:border-zinc-700">
              <div className="text-xs text-zinc-600 dark:text-zinc-400 mb-1">Time</div>
              <div className="text-lg font-bold text-zinc-900 dark:text-zinc-100">
                {formatTime(timeElapsed)}
              </div>
            </div>
            
            <div className="bg-white dark:bg-zinc-800/50 rounded-lg p-3 border border-zinc-200 dark:border-zinc-700">
              <div className="text-xs text-zinc-600 dark:text-zinc-400 mb-1">Credits</div>
              <div className="text-lg font-bold text-zinc-900 dark:text-zinc-100">
                {creditsUsed}
              </div>
            </div>
          </div>

          {/* Recently Crawled */}
          {recentPages.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
                Recently Crawled
              </h4>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {recentPages.map((page, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 text-xs text-zinc-600 dark:text-zinc-400 bg-white dark:bg-zinc-800/30 rounded px-2 py-1.5 animate-fade-in"
                    style={{ animationDelay: `${i * 50}ms` }}
                  >
                    <span className={page.status === 'completed' ? 'text-green-500' : 'text-yellow-500'}>
                      {page.status === 'completed' ? '✓' : '⏳'}
                    </span>
                    <span className="truncate">{page.url}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Job Details */}
          <div className="pt-3 border-t border-zinc-200 dark:border-zinc-700 space-y-1">
            <div className="text-xs text-zinc-600 dark:text-zinc-400">
              <span className="font-medium">Job ID:</span>{' '}
              <code className="bg-zinc-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded text-[10px]">
                {jobId}
              </code>
            </div>
            {expiresAt && (
              <div className="text-xs text-zinc-600 dark:text-zinc-400">
                <span className="font-medium">Expires:</span>{' '}
                {new Date(expiresAt).toLocaleString()}
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            {!isComplete && onCancel && (
              <button
                onClick={onCancel}
                className="px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30 hover:bg-red-100 dark:hover:bg-red-950/50 rounded-lg transition-colors border border-red-200 dark:border-red-800"
              >
                Cancel Crawl
              </button>
            )}
            {isComplete && (
              <div className={`px-4 py-2 text-sm font-medium rounded-lg ${
                status === 'completed' 
                  ? 'bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-800'
                  : 'bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800'
              }`}>
                {status === 'completed' 
                  ? '✨ All pages embedded and stored in Qdrant'
                  : '❌ Crawl failed - check logs for details'
                }
              </div>
            )}
          </div>

          {/* Live indicator */}
          {isActive && (
            <div className="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-pink-500 rounded-full animate-pulse" style={{ animationDelay: '300ms' }} />
              </div>
              <span>Pages are being embedded and stored in Qdrant...</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
