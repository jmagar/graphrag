interface CitationProps {
  number: number;
  title: string;
  url?: string;
  preview?: string;
  onClick?: () => void;
}

export function Citation({ number, title, url, preview, onClick }: CitationProps) {
  const hasTooltipContent = url || preview;

  return (
    <div className="group relative inline-block">
      <button
        onClick={onClick}
        aria-label={`Citation ${number}: ${title}${url ? ` - ${url}` : ''}`}
        className="inline-flex items-center gap-1.5 h-7 px-2.5 bg-gradient-to-r from-emerald-50 to-emerald-100/50 dark:from-emerald-500/10 dark:to-emerald-500/5 hover:from-emerald-100 hover:to-emerald-100 dark:hover:from-emerald-500/20 dark:hover:to-emerald-500/10 border border-emerald-200/50 dark:border-emerald-500/20 rounded-lg text-xs transition-all hover:shadow-sm hover:shadow-emerald-500/10"
      >
        <span className="w-4 h-4 rounded bg-emerald-500 text-white flex items-center justify-center text-[9px] font-bold shadow-sm">
          {number}
        </span>
        <span className="font-medium text-emerald-900 dark:text-emerald-300 text-xs">{title}</span>
        <svg className="w-2.5 h-2.5 text-emerald-600 dark:text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
        </svg>
      </button>

      {/* CSS Tooltip */}
      {hasTooltipContent && (
        <div className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-50">
          <div className="max-w-sm overflow-hidden rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 px-4 py-3 text-sm shadow-xl">
            <div className="space-y-2">
              <div className="flex items-start gap-2">
                <span className="flex-shrink-0 w-5 h-5 rounded-md bg-emerald-500 text-white flex items-center justify-center text-[10px] font-bold">
                  {number}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-zinc-900 dark:text-zinc-100 leading-tight">
                    {title}
                  </p>
                  {url && (
                    <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1 truncate">
                      {url}
                    </p>
                  )}
                </div>
              </div>
              {preview && (
                <p className="text-xs text-zinc-700 dark:text-zinc-300 leading-relaxed line-clamp-3">
                  {preview}
                </p>
              )}
            </div>
          </div>
          {/* Arrow */}
          <div className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-l-8 border-r-8 border-t-8 border-transparent border-t-white dark:border-t-zinc-950"></div>
        </div>
      )}
    </div>
  );
}
