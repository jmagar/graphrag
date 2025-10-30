import { Avatar } from './Avatar';

interface TypingIndicatorProps {
  message?: string;
}

export function TypingIndicator({ message = 'Thinking...' }: TypingIndicatorProps) {
  return (
    <div className="message-animate flex gap-4">
      <Avatar type="ai" />
      <div className="flex items-center gap-2 pt-2">
        <span className="text-sm text-zinc-500 dark:text-zinc-400">{message}</span>
        <div className="flex gap-1">
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  );
}
