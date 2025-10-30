import { Avatar } from './Avatar';
import { Citation } from './Citation';
import { MessageActions } from './MessageActions';
import { Artifact } from './Artifact';

interface AIMessageProps {
  content: string[];
  citations?: Array<{ number: number; title: string }>;
  timestamp?: string;
  artifact?: {
    type: 'markdown' | 'code' | 'text' | 'json' | 'html';
    content: string;
    language?: string;
    title?: string;
    url?: string;
  };
}

export function AIMessage({ content, citations, timestamp = "2:34 PM", artifact }: AIMessageProps) {
  const handleCopy = () => {
    const textToCopy = artifact ? artifact.content : content.join('\n\n');
    navigator.clipboard.writeText(textToCopy);
  };

  return (
    <div className="message-animate flex gap-2 md:gap-4 group">
      <div className="flex-shrink-0">
        <Avatar type="ai" />
      </div>
      <div className="flex-1 min-w-0 space-y-2 md:space-y-3 pt-0.5">
        <div className="text-sm md:text-base leading-relaxed text-zinc-800 dark:text-zinc-100 space-y-2 md:space-y-3">
          {content.map((paragraph, index) => (
            <p
              key={index}
              className="animate-fade-in break-words"
              style={{ animationDelay: `${index * 0.1}s` }}
              dangerouslySetInnerHTML={{ __html: paragraph }}
            />
          ))}
        </div>

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
    </div>
  );
}
