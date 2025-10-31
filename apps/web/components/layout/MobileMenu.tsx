"use client";

interface MobileMenuProps {
  onClick: () => void;
  side?: 'left' | 'right';
}

export function MobileMenu({ onClick, side = 'left' }: MobileMenuProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="lg:hidden p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg transition-colors active:scale-95"
      aria-label={side === 'left' ? 'Open sidebar' : 'Open workflows'}
    >
      {side === 'left' ? (
        <svg className="w-6 h-6 text-zinc-600 dark:text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16"/>
        </svg>
      ) : (
        <svg className="w-6 h-6 text-zinc-600 dark:text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"/>
        </svg>
      )}
    </button>
  );
}
