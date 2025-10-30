'use client';

import { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

type ArtifactType = 'markdown' | 'code' | 'text' | 'json' | 'html';

interface ArtifactProps {
  type: ArtifactType;
  content: string;
  language?: string;
  title?: string;
  url?: string;
}

export function Artifact({ type, content, language = 'text', title, url }: ArtifactProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderContent = () => {
    switch (type) {
      case 'markdown':
        return (
          <div className="p-4 overflow-auto max-h-[600px] bg-white dark:bg-zinc-900">
            <div className="prose prose-sm max-w-none prose-headings:text-zinc-900 prose-p:text-zinc-800 prose-a:text-blue-600 prose-strong:text-zinc-900 prose-code:text-zinc-900 prose-pre:bg-zinc-100 prose-li:text-zinc-800">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // Remove all images (including logos, flags, etc.)
                  img: () => null,
                  
                  // Code blocks with syntax highlighting
                  code({ node, inline, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '');
                    return !inline && match ? (
                      <SyntaxHighlighter
                        style={vscDarkPlus as any}
                        language={match[1]}
                        PreTag="div"
                        {...props}
                      >
                        {String(children).replace(/\n$/, '')}
                      </SyntaxHighlighter>
                    ) : (
                      <code className="bg-zinc-100 text-zinc-900 px-1.5 py-0.5 rounded text-xs" {...props}>
                        {children}
                      </code>
                    );
                  },
                  
                  // Explicit colors for headings
                  h1: ({ children }) => <h1 className="text-2xl font-bold text-zinc-900 mt-6 mb-4">{children}</h1>,
                  h2: ({ children }) => <h2 className="text-xl font-bold text-zinc-900 mt-5 mb-3">{children}</h2>,
                  h3: ({ children }) => <h3 className="text-lg font-semibold text-zinc-900 mt-4 mb-2">{children}</h3>,
                  
                  // Paragraph styling
                  p: ({ children }) => <p className="text-zinc-800 leading-relaxed mb-4">{children}</p>,
                  
                  // List styling
                  ul: ({ children }) => <ul className="list-disc list-inside text-zinc-800 mb-4 space-y-1">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal list-inside text-zinc-800 mb-4 space-y-1">{children}</ol>,
                  li: ({ children }) => <li className="text-zinc-800">{children}</li>,
                  
                  // Links
                  a: ({ href, children }) => (
                    <a href={href} className="text-blue-600 hover:text-blue-700 underline" target="_blank" rel="noopener noreferrer">
                      {children}
                    </a>
                  ),
                }}
              >
                {content}
              </ReactMarkdown>
            </div>
          </div>
        );

      case 'code':
      case 'json':
      case 'html':
        return (
          <div className="overflow-auto max-h-[600px]">
            <SyntaxHighlighter
              language={type === 'json' ? 'json' : type === 'html' ? 'html' : language}
              style={vscDarkPlus as any}
              customStyle={{
                margin: 0,
                borderRadius: '0 0 0.5rem 0.5rem',
                fontSize: '0.875rem',
              }}
              showLineNumbers
            >
              {content}
            </SyntaxHighlighter>
          </div>
        );

      case 'text':
      default:
        return (
          <div className="p-4 overflow-auto max-h-[600px]">
            <pre className="text-sm text-zinc-800 dark:text-zinc-200 whitespace-pre-wrap font-mono">
              {content}
            </pre>
          </div>
        );
    }
  };

  return (
    <div className="my-4 border border-zinc-200 dark:border-zinc-800 rounded-lg overflow-hidden bg-white dark:bg-zinc-950 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-zinc-50 dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            {type === 'markdown' && (
              <svg className="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            )}
            {(type === 'code' || type === 'json' || type === 'html') && (
              <svg className="w-4 h-4 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
            )}
            <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
              {title || (type === 'code' ? language.toUpperCase() : type.toUpperCase())}
            </span>
          </div>
          {url && (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-600 dark:text-blue-400 hover:underline truncate max-w-xs"
            >
              {url}
            </a>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-2 py-1 text-xs font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded transition-colors"
          >
            {copied ? (
              <>
                <svg className="w-3.5 h-3.5 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Copied
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Copy
              </>
            )}
          </button>
        </div>
      </div>

      {/* Content */}
      {renderContent()}
    </div>
  );
}
