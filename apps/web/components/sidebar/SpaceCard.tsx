interface SpaceCardProps {
  name: string;
  icon: React.ReactNode;
  sourceCount: number;
  color: 'blue' | 'emerald' | 'purple';
  isActive?: boolean;
  onClick?: () => void;
}

export function SpaceCard({ name, icon, sourceCount, color, isActive = false, onClick }: SpaceCardProps) {
  const colorClasses = {
    blue: {
      bg: isActive ? 'bg-blue-50 dark:bg-blue-500/10' : 'hover:bg-zinc-50 dark:hover:bg-zinc-900',
      border: isActive ? 'border-blue-200 dark:border-blue-500/20' : 'border-transparent',
      iconBg: 'bg-blue-500/20',
      iconColor: 'text-blue-600 dark:text-blue-400',
      textColor: isActive ? 'text-zinc-900 dark:text-zinc-100' : 'text-zinc-700 dark:text-zinc-300',
    },
    emerald: {
      bg: 'hover:bg-zinc-50 dark:hover:bg-zinc-900',
      border: 'border-transparent',
      iconBg: 'bg-emerald-500/10',
      iconColor: 'text-emerald-600 dark:text-emerald-400',
      textColor: 'text-zinc-700 dark:text-zinc-300',
    },
    purple: {
      bg: 'hover:bg-zinc-50 dark:hover:bg-zinc-900',
      border: 'border-transparent',
      iconBg: 'bg-purple-500/10',
      iconColor: 'text-purple-600 dark:text-purple-400',
      textColor: 'text-zinc-700 dark:text-zinc-300',
    },
  };

  const classes = colorClasses[color];

  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-2.5 text-xs p-2 rounded-lg cursor-pointer transition-colors ${classes.bg} border ${classes.border}`}
    >
      <div className={`w-7 h-7 rounded-md flex items-center justify-center shrink-0 ${classes.iconBg}`}>
        <div className={classes.iconColor}>{icon}</div>
      </div>
      <div className="flex-1 text-left">
        <div className={`font-semibold ${classes.textColor}`}>{name}</div>
        <div className="text-[10px] text-zinc-500 dark:text-zinc-400">{sourceCount} sources</div>
      </div>
    </button>
  );
}
