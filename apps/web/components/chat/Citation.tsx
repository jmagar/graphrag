interface CitationProps {
  number: number;
  title: string;
  onClick?: () => void;
}

export function Citation({ number, title, onClick }: CitationProps) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1.5 h-7 px-2.5 bg-gradient-to-r from-emerald-50 to-emerald-100/50 dark:from-emerald-500/10 dark:to-emerald-500/5 hover:from-emerald-100 hover:to-emerald-100 dark:hover:from-emerald-500/20 dark:hover:to-emerald-500/10 border border-emerald-200/50 dark:border-emerald-500/20 rounded-lg text-xs transition-all hover:shadow-sm hover:shadow-emerald-500/10"
    >
      <span className="w-4 h-4 rounded bg-emerald-500 text-white flex items-center justify-center text-[9px] font-bold shadow-sm">
        {number}
      </span>
      <span className="font-medium text-emerald-900 dark:text-emerald-300 text-xs">{title}</span>
      <svg className="w-2.5 h-2.5 text-emerald-600 dark:text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
      </svg>
    </button>
  );
}
