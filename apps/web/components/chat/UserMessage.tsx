import { memo } from 'react';
import { Avatar } from './Avatar';
import { ToolCall } from './ToolCall';

/**
 * UserMessage - Refactored for consistency with prompt-kit migration (Phase 8 - 2025-10-30)
 * 
 * Note: This component uses direct DIV elements (not prompt-kit Message) because:
 * - User messages are simple text without markdown/code rendering
 * - Custom styling (blue gradient) is specific to user messages
 * - Message component is optimized for AI messages with markdown content
 * 
 * However, this refactoring consolidates styling and improves accessibility:
 * - Better semantic HTML with aria-label
 * - Consistent hover animations (group-hover)
 * - Proper timestamp and edit button management
 * - Memoization prevents unnecessary re-renders
 * 
 * Preserved Features:
 * - Slash command parsing and display with ToolCall
 * - Edit button with optional callback
 * - Timestamps
 * - User avatar display
 * - Responsive design (mobile/desktop)
 * - Smooth message animations
 */

interface UserMessageProps {
  content: string;
  timestamp?: string;
  onEdit?: () => void;
}

const UserMessageComponent = ({ content, timestamp = "2:35 PM", onEdit }: UserMessageProps) => {
  // Parse slash commands from content
  const parseContent = (): { isCommand: false } | { isCommand: true; command: string; args: string } => {
    const commandMatch = content.match(/^(\/\w+)\s*(.*)$/);
    if (commandMatch) {
      return {
        isCommand: true,
        command: commandMatch[1],
        args: commandMatch[2] || ''
      };
    }
    return { isCommand: false };
  };

  const parsed = parseContent();

  return (
    <article
      aria-label={`User message${timestamp ? ` at ${timestamp}` : ''}`}
      className="message-animate flex justify-end gap-2 md:gap-4 group"
    >
      <div className="max-w-[85%] md:max-w-2xl">
        {/* Use Message component from prompt-kit for consistency */}
        {parsed.isCommand ? (
          <div className="inline-flex items-center gap-2 px-3 md:px-4 py-2 md:py-2.5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 shadow-md rounded-xl">
            <ToolCall command={parsed.command} args={parsed.args} />
          </div>
        ) : (
          <div className="inline-block px-3 md:px-4 py-2 md:py-2.5 bg-gradient-to-br from-blue-600 to-blue-700 shadow-lg shadow-blue-500/25 dark:shadow-blue-500/40 rounded-xl">
            <p className="text-sm md:text-base text-white font-medium break-words">{content}</p>
          </div>
        )}

        {/* Actions: Edit button and timestamp */}
        <div className="flex items-center justify-end gap-2 mt-1.5 md:mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
          {onEdit && (
            <button
              type="button"
              onClick={onEdit}
              aria-label="Edit message"
              className="p-1.5 md:p-1 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors active:scale-95"
              title="Edit message"
            >
              <svg className="w-4 h-4 md:w-3.5 md:h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
              </svg>
            </button>
          )}
          <div className="text-xs text-zinc-400">{timestamp}</div>
        </div>
      </div>

      {/* User Avatar */}
      <div className="flex-shrink-0" aria-hidden="true">
        <Avatar type="user" />
      </div>
    </article>
  );
};

// Export memoized component
export const UserMessage = memo(UserMessageComponent);
