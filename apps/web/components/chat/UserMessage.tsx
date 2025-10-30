import { Avatar } from './Avatar';

interface UserMessageProps {
  content: string;
  timestamp?: string;
  onEdit?: () => void;
}

export function UserMessage({ content, timestamp = "2:35 PM", onEdit }: UserMessageProps) {
  return (
    <div className="message-animate flex justify-end gap-4 group">
      <div className="max-w-2xl">
        <div className="inline-block px-4 py-2.5 bg-gradient-to-br from-blue-600 to-blue-700 shadow-lg shadow-blue-500/25 dark:shadow-blue-500/40 rounded-xl">
          <p className="text-sm text-white font-medium">{content}</p>
        </div>
        <div className="flex items-center justify-end gap-2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
          {onEdit && (
            <button
              onClick={onEdit}
              className="p-1 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
              title="Edit"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
              </svg>
            </button>
          )}
          <div className="text-xs text-zinc-400">{timestamp}</div>
        </div>
      </div>
      <Avatar type="user" />
    </div>
  );
}
