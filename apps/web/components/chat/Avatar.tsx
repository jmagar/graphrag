interface AvatarProps {
  type: 'ai' | 'user';
  className?: string;
}

export function Avatar({ type, className = '' }: AvatarProps) {
  if (type === 'ai') {
    return (
      <div className={`w-8 h-8 rounded-xl overflow-hidden shrink-0 shadow-md shadow-blue-500/20 dark:shadow-blue-500/40 ring-1 ring-white/50 dark:ring-zinc-900/50 ${className}`}>
        <div className="w-full h-full bg-gradient-to-br from-zinc-700 to-zinc-800 flex items-center justify-center relative">
          {/* Mandalorian Helmet */}
          <div className="relative">
            <div className="w-5 h-5 bg-zinc-400 rounded-sm relative">
              {/* T-shaped Visor */}
              <div className="absolute top-1.5 left-1/2 -translate-x-1/2 w-3 h-0.5 bg-zinc-900 rounded-full" />
              <div className="absolute top-2 left-1/2 -translate-x-1/2 w-1 h-2 bg-zinc-900 rounded-sm" />
              {/* Side details */}
              <div className="absolute top-0.5 left-0 w-1 h-1 bg-zinc-500 rounded-full" />
              <div className="absolute top-0.5 right-0 w-1 h-1 bg-zinc-500 rounded-full" />
              {/* Chin piece */}
              <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-3 h-1 bg-zinc-500 rounded-b-sm" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // User avatar - Grogu (Baby Yoda)
  return (
    <div className={`w-8 h-8 rounded-xl overflow-hidden shrink-0 shadow-md ring-1 ring-white/10 dark:ring-zinc-700/50 ${className}`}>
      <div className="w-full h-full bg-gradient-to-br from-emerald-600 to-emerald-700 flex items-center justify-center relative">
        {/* Grogu (Baby Yoda) */}
        <div className="relative">
          {/* Head */}
          <div className="w-5 h-4 bg-emerald-400 rounded-full relative">
            {/* Eyes */}
            <div className="absolute top-1 left-0.5 w-1 h-1.5 bg-zinc-900 rounded-full" />
            <div className="absolute top-1 right-0.5 w-1 h-1.5 bg-zinc-900 rounded-full" />
            {/* Left Ear */}
            <div className="absolute -left-1.5 -top-1 w-2 h-3 bg-emerald-400 rounded-full transform -rotate-12" />
            {/* Right Ear */}
            <div className="absolute -right-1.5 -top-1 w-2 h-3 bg-emerald-400 rounded-full transform rotate-12" />
          </div>
        </div>
      </div>
    </div>
  );
}
