import { memo } from 'react';
import { Avatar } from './Avatar';
import { Citation } from './Citation';
import { MessageActions } from './MessageActions';
import { Artifact } from './Artifact';
import { ToolCall } from './ToolCall';
import { CrawlProgress } from '../crawl/CrawlProgress';
import { CodeBlock } from './CodeBlock';
import { MermaidDiagram } from './MermaidDiagram';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import type { ContentSegment } from '@/app/page';

// Helper to check if content is ContentSegment array
function isContentSegmentArray(content: string | string[] | ContentSegment[]): content is ContentSegment[] {
  return Array.isArray(content) && content.length > 0 && typeof content[0] === 'object' && 'type' in content[0];
}

interface AIMessageProps {
  content: string | string[] | ContentSegment[];
  citations?: Array<{ number: number; title: string; url?: string; preview?: string }>;
  timestamp?: string;
  isStreaming?: boolean;
  artifact?: {
    type: 'markdown' | 'code' | 'text' | 'json' | 'html';
    content: string;
    language?: string;
    title?: string;
    url?: string;
  };
  toolCalls?: Array<{
    command: string;
    args?: string;
    status?: 'running' | 'complete' | 'error';
  }>;
  crawl?: {
    jobId: string;
    status: string;
    url: string;
    data?: {
      completed: number;
      total: number;
      creditsUsed: number;
      expiresAt?: string;
      recentPages?: Array<{ url: string; status: string }>;
    };
  };
  onCancelCrawl?: (jobId: string) => void;
}

const AIMessageComponent = ({ content, citations, timestamp = "2:34 PM", isStreaming = false, artifact, toolCalls, crawl, onCancelCrawl }: AIMessageProps) => {
  const handleCopy = async () => {
    let textToCopy = '';
    if (artifact) {
      textToCopy = artifact.content;
    } else if (isContentSegmentArray(content)) {
      textToCopy = content
        .filter(seg => seg.type === 'text')
        .map(seg => seg.type === 'text' ? seg.text : '')
        .join('\n\n');
    } else {
      textToCopy = Array.isArray(content) ? content.join('\n\n') : content;
    }

    try {
      await navigator.clipboard.writeText(textToCopy);
    } catch (error) {
      throw new Error('Failed to copy message');
    }
  };

  // Check if we should show typing indicator
  const hasNoContent = isContentSegmentArray(content)
    ? content.length === 0
    : Array.isArray(content)
    ? content.length === 0 || (content.length === 1 && content[0] === '')
    : content === '';
  const showTypingIndicator = isStreaming && hasNoContent && (!toolCalls || toolCalls.length === 0);

  return (
    <article
      role="article"
      aria-label={`AI assistant response${timestamp ? ` at ${timestamp}` : ''}`}
      className="message-animate flex gap-3 md:gap-5 group px-4 md:px-6 py-4 md:py-5 hover:bg-zinc-50/50 dark:hover:bg-zinc-900/30 rounded-2xl transition-colors duration-200"
    >
      <div className="flex-shrink-0" aria-hidden="true">
        <Avatar type="ai" />
      </div>
      <div className="flex-1 min-w-0 space-y-3 md:space-y-4 pt-1">
        {/* Show typing indicator when streaming with no content */}
        {showTypingIndicator ? (
          <div
            role="status"
            aria-live="polite"
            aria-atomic="true"
            className="flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-zinc-50 to-transparent dark:from-zinc-900/50 dark:to-transparent rounded-xl border border-zinc-200/50 dark:border-zinc-700/50 backdrop-blur-sm"
          >
            <div className="flex gap-1.5" aria-hidden="true">
              <div className="w-2 h-2 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full animate-bounce shadow-sm motion-reduce:animate-pulse" style={{ animationDelay: '0ms', animationDuration: '0.6s' }} />
              <div className="w-2 h-2 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full animate-bounce shadow-sm motion-reduce:animate-pulse" style={{ animationDelay: '150ms', animationDuration: '0.6s' }} />
              <div className="w-2 h-2 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full animate-bounce shadow-sm motion-reduce:animate-pulse" style={{ animationDelay: '300ms', animationDuration: '0.6s' }} />
            </div>
            <span className="text-sm font-medium text-zinc-700 dark:text-zinc-200">
              AI assistant is thinking...
            </span>
          </div>
        ) : isContentSegmentArray(content) ? (
          // New inline rendering for ContentSegment[]
          <div
            role="log"
            aria-live="polite"
            aria-atomic="false"
            aria-relevant="additions text"
            className="space-y-3 md:space-y-4"
          >
            {content.map((segment, index) => (
              <div key={index}>
                {segment.type === 'tool' ? (
                  // Render tool call inline
                  <div className="my-2">
                    <ToolCall
                      command={segment.command}
                      args={segment.args}
                      status={segment.status || 'complete'}
                    />
                  </div>
                ) : (
                  // Render text segment
                  <div
                    className="animate-stream-in break-words prose prose-base max-w-none text-[15px] md:text-base"
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm, remarkMath]}
                      rehypePlugins={[rehypeKatex]}
                      components={{
                        // Remove all images
                        img: () => null,

                        // Code blocks - use new CodeBlock or Mermaid
                        code({ node, className, children, ...props }: any) {
                          const match = /language-(\w+)/.exec(className || '');
                          const inline = !match;
                          const language = match ? match[1] : 'text';
                          const value = String(children).replace(/\n$/, '');

                          // Mermaid diagrams
                          if (language === 'mermaid') {
                            return <MermaidDiagram chart={value} />;
                          }

                          // Regular code blocks
                          return (
                            <CodeBlock
                              language={language}
                              value={value}
                              inline={inline}
                            />
                          );
                        },

                        // Headings with better spacing
                        h1: ({ children }) => <h1 className="text-2xl md:text-3xl font-bold text-zinc-900 dark:text-zinc-50 mt-8 mb-5 tracking-tight">{children}</h1>,
                        h2: ({ children }) => <h2 className="text-xl md:text-2xl font-bold text-zinc-900 dark:text-zinc-50 mt-6 mb-4 tracking-tight">{children}</h2>,
                        h3: ({ children }) => <h3 className="text-lg md:text-xl font-semibold text-zinc-800 dark:text-zinc-100 mt-5 mb-3">{children}</h3>,

                        // Paragraph with better line height and contrast
                        p: ({ children }) => <p className="text-zinc-900/90 dark:text-zinc-100/90 leading-[1.7] mb-3">{children}</p>,

                        // Lists with better spacing
                        ul: ({ children }) => <ul className="list-disc list-outside ml-5 text-zinc-800 dark:text-zinc-200 mb-3 space-y-2">{children}</ul>,
                        ol: ({ children }) => <ol className="list-decimal list-outside ml-5 text-zinc-800 dark:text-zinc-200 mb-3 space-y-2">{children}</ol>,
                        li: ({ children }) => <li className="text-zinc-800 dark:text-zinc-200 pl-2">{children}</li>,

                        // Links with better underline
                        a: ({ href, children }) => (
                          <a
                            href={href}
                            className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 underline decoration-blue-600/40 dark:decoration-blue-400/40 hover:decoration-blue-600 dark:hover:decoration-blue-400 underline-offset-2 transition-all duration-150"
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            {children}
                          </a>
                        ),

                        // Strong with proper contrast
                        strong: ({ children }) => <strong className="font-semibold text-zinc-900 dark:text-white">{children}</strong>,
                      }}
                    >
                      {segment.text}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          // Legacy rendering for string[] (backward compatibility)
          <div
            role="log"
            aria-live="polite"
            aria-atomic="false"
            aria-relevant="additions text"
            className="prose prose-base max-w-none text-[15px] md:text-base space-y-3 md:space-y-4"
          >
            {/* Render tool calls at top for backward compatibility */}
            {toolCalls && toolCalls.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-2">
                {toolCalls.map((toolCall, index) => (
                  <ToolCall
                    key={index}
                    command={toolCall.command}
                    args={toolCall.args}
                    status={toolCall.status || 'complete'}
                  />
                ))}
              </div>
            )}
            {(Array.isArray(content) ? content : [content]).map((paragraph, index) => (
              <div
                key={index}
                className="animate-stream-in break-words"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkMath]}
                  rehypePlugins={[rehypeKatex]}
                  components={{
                    // Remove all images
                    img: () => null,

                    // Code blocks - use new CodeBlock or Mermaid
                    code({ node, className, children, ...props }: any) {
                      const match = /language-(\w+)/.exec(className || '');
                      const inline = !match;
                      const language = match ? match[1] : 'text';
                      const value = String(children).replace(/\n$/, '');

                      // Mermaid diagrams
                      if (language === 'mermaid') {
                        return <MermaidDiagram chart={value} />;
                      }

                      // Regular code blocks
                      return (
                        <CodeBlock
                          language={language}
                          value={value}
                          inline={inline}
                        />
                      );
                    },

                    // Headings with better spacing
                    h1: ({ children }) => <h1 className="text-2xl md:text-3xl font-bold text-zinc-900 dark:text-zinc-50 mt-8 mb-5 tracking-tight">{children}</h1>,
                    h2: ({ children }) => <h2 className="text-xl md:text-2xl font-bold text-zinc-900 dark:text-zinc-50 mt-6 mb-4 tracking-tight">{children}</h2>,
                    h3: ({ children }) => <h3 className="text-lg md:text-xl font-semibold text-zinc-800 dark:text-zinc-100 mt-5 mb-3">{children}</h3>,

                    // Paragraph with better line height and contrast
                    p: ({ children }) => <p className="text-zinc-900/90 dark:text-zinc-100/90 leading-[1.7] mb-3">{children}</p>,

                    // Lists with better spacing
                    ul: ({ children }) => <ul className="list-disc list-outside ml-5 text-zinc-800 dark:text-zinc-200 mb-3 space-y-2">{children}</ul>,
                    ol: ({ children }) => <ol className="list-decimal list-outside ml-5 text-zinc-800 dark:text-zinc-200 mb-3 space-y-2">{children}</ol>,
                    li: ({ children }) => <li className="text-zinc-800 dark:text-zinc-200 pl-2">{children}</li>,

                    // Links with better underline
                    a: ({ href, children }) => (
                      <a
                        href={href}
                        className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 underline decoration-blue-600/40 dark:decoration-blue-400/40 hover:decoration-blue-600 dark:hover:decoration-blue-400 underline-offset-2 transition-all duration-150"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {children}
                      </a>
                    ),

                    // Strong with proper contrast
                    strong: ({ children }) => <strong className="font-semibold text-zinc-900 dark:text-white">{children}</strong>,
                  }}
                >
                  {paragraph}
                </ReactMarkdown>
              </div>
            ))}
          </div>
        )}

        {/* Render crawl progress if present */}
        {crawl && crawl.data && (
          <CrawlProgress
            jobId={crawl.jobId}
            url={crawl.url}
            status={crawl.status}
            completed={crawl.data.completed}
            total={crawl.data.total}
            creditsUsed={crawl.data.creditsUsed}
            expiresAt={crawl.data.expiresAt}
            recentPages={crawl.data.recentPages}
            onCancel={onCancelCrawl ? () => onCancelCrawl(crawl.jobId) : undefined}
          />
        )}

        {/* Render artifact if present */}
        {artifact && (
          <Artifact
            type={artifact.type}
            content={artifact.content}
            language={artifact.language}
            title={artifact.title}
            url={artifact.url}
          />
        )}
        
        {citations && citations.length > 0 && (
          <div className="flex flex-wrap gap-1.5 md:gap-2">
            {citations.map((citation) => (
              <Citation
                key={citation.number}
                number={citation.number}
                title={citation.title}
                url={citation.url}
                preview={citation.preview}
              />
            ))}
          </div>
        )}
        
        <MessageActions
          timestamp={timestamp}
          onCopy={handleCopy}
          onRegenerate={() => {}}
        />
      </div>
    </article>
  );
};

// Export memoized component
export const AIMessage = memo(AIMessageComponent);
