interface SidebarHeaderProps {
  onAddSource?: () => void;
}

export function SidebarHeader({ onAddSource }: SidebarHeaderProps) {
  return (
    <div className="h-14 border-b border-zinc-200 dark:border-zinc-800/80 flex items-center justify-between px-4">
      <div className="flex items-center gap-2">
        <div className="w-6 h-6 rounded bg-gradient-to-br from-blue-600 to-blue-700 flex items-center justify-center">
          <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M13 10V3L4 14h7v7l9-11h-7z"/>
          </svg>
        </div>
        <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">GraphRAG</span>
      </div>
      <button 
        onClick={onAddSource}
        className="w-8 h-8 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-600 text-white rounded-lg flex items-center justify-center transition-all shadow-sm hover:shadow-md"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M12 4v16m8-8H4"/>
        </svg>
      </button>
    </div>
  );
}
