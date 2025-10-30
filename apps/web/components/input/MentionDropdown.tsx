interface Source {
  name: string;
  chunks: number;
  icon: React.ReactNode;
  color: string;
}

interface MentionDropdownProps {
  onSelect: (source: string) => void;
}

const sources: Source[] = [
  {
    name: 'Getting Started Guide',
    chunks: 247,
    color: 'emerald',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
      </svg>
    ),
  },
  {
    name: 'API Documentation',
    chunks: 189,
    color: 'blue',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>
      </svg>
    ),
  },
];

export function MentionDropdown({ onSelect }: MentionDropdownProps) {
  return (
    <div className="absolute bottom-full left-0 mb-2 w-72 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-xl overflow-hidden">
      <div className="p-2 border-b border-zinc-200 dark:border-zinc-800">
        <div className="text-xs font-medium text-zinc-500 px-2 py-1">Mention a source</div>
      </div>
      <div className="mention-dropdown overflow-y-auto custom-scroll max-h-[300px]">
        {sources.map((source) => (
          <button
            key={source.name}
            onClick={() => onSelect(source.name)}
            className="w-full px-3 py-2 hover:bg-zinc-50 dark:hover:bg-zinc-800 text-left flex items-center gap-2.5 transition-colors"
          >
            <div className={`w-8 h-8 rounded-md bg-${source.color}-500/10 flex items-center justify-center shrink-0`}>
              <div className={`text-${source.color}-600 dark:text-${source.color}-400`}>{source.icon}</div>
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100 truncate">{source.name}</div>
              <div className="text-xs text-zinc-500 truncate">{source.chunks} chunks</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
