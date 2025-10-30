'use client';

import { useState, useEffect } from 'react';
import { codeToHtml } from 'shiki';

interface CodeBlockProps {
  language: string;
  value: string;
  inline?: boolean;
  filename?: string;
}

export function CodeBlock({ language, value, inline, filename }: CodeBlockProps) {
  const [html, setHtml] = useState('');
  const [copied, setCopied] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!inline) {
      const highlight = async () => {
        try {
          const result = await codeToHtml(value, {
            lang: language || 'text',
            theme: 'dark-plus',
          });
          setHtml(result);
        } catch (error) {
          // Fallback for unknown languages
          const fallback = await codeToHtml(value, {
            lang: 'text',
            theme: 'dark-plus',
          });
          setHtml(fallback);
        } finally {
          setIsLoading(false);
        }
      };

      highlight();
    }
  }, [value, language, inline]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      throw new Error('Failed to copy code');
    }
  };

  // Inline code
  if (inline) {
    return (
      <code className="bg-zinc-100 dark:bg-zinc-800/80 text-zinc-900 dark:text-zinc-50 px-2 py-0.5 rounded-md text-[13px] font-mono border border-zinc-200 dark:border-zinc-700/50">
        {value}
      </code>
    );
  }

  // Block code
  return (
    <div className="my-4 rounded-lg overflow-hidden border border-zinc-200 dark:border-zinc-800">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-zinc-50 dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center gap-2">
          {filename && (
            <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
              {filename}
            </span>
          )}
          {!filename && language && (
            <span className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
              {language.toUpperCase()}
            </span>
          )}
        </div>
        <button
          onClick={handleCopy}
          aria-label={copied ? 'Code copied to clipboard' : 'Copy code to clipboard'}
          className="flex items-center gap-1.5 px-2 py-1 text-xs text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded transition-colors"
        >
          {copied ? (
            <>
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>Copied</span>
            </>
          ) : (
            <>
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Code content */}
      <div className="overflow-x-auto">
        {isLoading ? (
          <div className="p-4 bg-[#1e1e1e] animate-pulse">
            <div className="h-4 bg-zinc-700 rounded w-3/4 mb-2" />
            <div className="h-4 bg-zinc-700 rounded w-1/2 mb-2" />
            <div className="h-4 bg-zinc-700 rounded w-2/3" />
          </div>
        ) : (
          <div
            className="shiki-code-block text-sm [&_pre]:m-0 [&_pre]:p-4 [&_pre]:bg-[#1e1e1e]"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        )}
      </div>
    </div>
  );
}
