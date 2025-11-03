import { memo } from 'react';
import { Avatar } from './Avatar';
import { MessageActions } from './MessageActions';
import { Artifact } from './Artifact';
import { ToolCall } from './ToolCall';
import { CrawlProgress } from '../crawl/CrawlProgress';
import { MermaidDiagram } from './MermaidDiagram';
import type { ContentSegment } from '@/components/layout/ClientLayout';

// Import prompt-kit components
import {
  Message,
  MessageContent,
} from '@/components/ui/message';
import { CodeBlockCode, CodeBlock } from '@/components/ui/code-block';
import { Loader } from '@/components/ui/loader';
import { Source, SourceTrigger, SourceContent } from '@/components/ui/source';
import { Image } from '@/components/ui/image';

// Helper to check if content is ContentSegment array
function isContentSegmentArray(content: string | string[] | ContentSegment[]): content is ContentSegment[] {
  return Array.isArray(content) && content.length > 0 && typeof content[0] === 'object' && 'type' in content[0];
}

// Shared markdown components for MessageContent
const markdownComponents = {
  // Render images with prompt-kit Image component
  img: (props: React.ImgHTMLAttributes<HTMLImageElement>) => {
    const { src, alt } = props;
    if (!src || typeof src !== 'string') return null;
    // Check if it's a data URL (base64)
    const isBase64 = src.startsWith('data:');
    if (isBase64) {
      const [mediaTypeStr, base64Data] = src.split(',');
      const mediaType = mediaTypeStr?.replace('data:', '').replace(';base64', '') || 'image/png';
      return <Image base64={base64Data} mediaType={mediaType} alt={alt || 'AI-generated image'} className="my-4" />;
    }
    // External URLs from markdown - domains are unpredictable, use regular img
    return (
      <img
        src={src}
        alt={alt || 'Image'}
        className="my-4 rounded-lg max-w-full h-auto"
      />
    );
  },

  // Code blocks - use prompt-kit CodeBlock
  code({ className, children }: { className?: string; children?: React.ReactNode }) {
    const match = /language-(\w+)/.exec(className || '');
    const inline = !match;
    const language = match ? match[1] : 'text';
    const value = String(children).replace(/\n$/, '');

    // Mermaid diagrams (keep custom)
    if (language === 'mermaid') {
      return <MermaidDiagram chart={value} />;
    }

    // Inline code
    if (inline) {
      return (
        <code className="bg-zinc-100 dark:bg-zinc-800/80 text-zinc-900 dark:text-zinc-50 px-2 py-0.5 rounded-md text-[13px] font-mono border border-zinc-200 dark:border-zinc-700/50">
          {children}
        </code>
      );
    }

    // Block code with prompt-kit
    return (
      <CodeBlock className="my-4">
        <CodeBlockCode code={value} language={language} theme="github-dark" />
      </CodeBlock>
    );
  },
};

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
    } catch {
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

  // Get text content for rendering
  const getTextContent = () => {
    if (isContentSegmentArray(content)) {
      return content
        .filter(seg => seg.type === 'text')
        .map(seg => seg.type === 'text' ? seg.text : '')
        .join('\n\n');
    }
    return Array.isArray(content) ? content.join('\n\n') : content;
  };

  return (
    <article
      aria-label={`AI assistant response${timestamp ? ` at ${timestamp}` : ''}`}
    >
      <Message className="message-animate group px-4 md:px-6 py-4 md:py-5 hover:bg-zinc-50/50 dark:hover:bg-zinc-900/30 rounded-2xl transition-colors duration-200">
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
            <Loader variant="dots" size="sm" className="text-blue-600 dark:text-blue-400" />
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
                  // Render text segment with prompt-kit Markdown
                  <MessageContent
                    markdown
                    className="animate-stream-in break-words prose prose-base max-w-none text-[15px] md:text-base bg-transparent p-0"
                    style={{ animationDelay: `${index * 50}ms` }}
                    components={markdownComponents}
                  >
                    {segment.text}
                  </MessageContent>
                )}
              </div>
            ))}
          </div>
        ) : (
          // Legacy rendering for string[] with prompt-kit components
          <MessageContent
            markdown
            className="prose prose-base max-w-none text-[15px] md:text-base bg-transparent p-0"
            components={markdownComponents}
          >
            {getTextContent()}
          </MessageContent>
        )}

        {/* Render tool calls at top for backward compatibility */}
        {toolCalls && toolCalls.length > 0 && !isContentSegmentArray(content) && (
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
              <Source key={citation.number} href={citation.url || '#'}>
                <SourceTrigger 
                  label={citation.number} 
                  showFavicon={false}
                  className="bg-gradient-to-r from-emerald-50 to-emerald-100/50 dark:from-emerald-500/10 dark:to-emerald-500/5 hover:from-emerald-100 hover:to-emerald-100 dark:hover:from-emerald-500/20 dark:hover:to-emerald-500/10 border-emerald-200/50 dark:border-emerald-500/20 text-emerald-900 dark:text-emerald-300"
                />
                {citation.url && (
                  <SourceContent 
                    title={citation.title}
                    description={citation.preview || `Source ${citation.number}`}
                  />
                )}
              </Source>
            ))}
          </div>
        )}
        
        <MessageActions
          timestamp={timestamp}
          onCopy={handleCopy}
          onRegenerate={() => {}}
        />
        </div>
      </Message>
    </article>
  );
};

// Export memoized component
export const AIMessage = memo(AIMessageComponent);
