import { Avatar } from './Avatar';
import { Citation } from './Citation';
import { MessageActions } from './MessageActions';

interface AIMessageProps {
  content: string[];
  citations?: Array<{ number: number; title: string }>;
  timestamp?: string;
}

export function AIMessage({ content, citations, timestamp = "2:34 PM" }: AIMessageProps) {
  const handleCopy = () => {
    navigator.clipboard.writeText(content.join('\n\n'));
  };

  return (
    <div className="message-animate flex gap-4 group">
      <Avatar type="ai" />
      <div className="flex-1 space-y-3 pt-0.5">
        <div className="text-sm leading-relaxed text-zinc-800 dark:text-zinc-100 space-y-3">
          {content.map((paragraph, index) => (
            <p
              key={index}
              className="animate-fade-in"
              style={{ animationDelay: `${index * 0.1}s` }}
              dangerouslySetInnerHTML={{ __html: paragraph }}
            />
          ))}
        </div>
        
        {citations && citations.length > 0 && (
          <div className="flex flex-wrap gap-2">
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
