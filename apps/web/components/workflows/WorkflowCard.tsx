interface WorkflowCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  color: 'blue' | 'emerald' | 'purple' | 'cyan' | 'amber' | 'rose' | 'indigo';
  onClick?: () => void;
}

export function WorkflowCard({ title, description, icon, color, onClick }: WorkflowCardProps) {
  const colorClasses = {
    blue: {
      border: 'hover:border-blue-500 dark:hover:border-blue-500',
      bg: 'hover:bg-blue-50/50 dark:hover:bg-blue-500/5',
      iconBg: 'bg-blue-500/10 group-hover:bg-blue-500/20',
      iconColor: 'text-blue-600 dark:text-blue-400'
    },
    emerald: {
      border: 'hover:border-emerald-500 dark:hover:border-emerald-500',
      bg: 'hover:bg-emerald-50/50 dark:hover:bg-emerald-500/5',
      iconBg: 'bg-emerald-500/10 group-hover:bg-emerald-500/20',
      iconColor: 'text-emerald-600 dark:text-emerald-400'
    },
    purple: {
      border: 'hover:border-purple-500 dark:hover:border-purple-500',
      bg: 'hover:bg-purple-50/50 dark:hover:bg-purple-500/5',
      iconBg: 'bg-purple-500/10 group-hover:bg-purple-500/20',
      iconColor: 'text-purple-600 dark:text-purple-400'
    },
    cyan: {
      border: 'hover:border-cyan-500 dark:hover:border-cyan-500',
      bg: 'hover:bg-cyan-50/50 dark:hover:bg-cyan-500/5',
      iconBg: 'bg-cyan-500/10 group-hover:bg-cyan-500/20',
      iconColor: 'text-cyan-600 dark:text-cyan-400'
    },
    amber: {
      border: 'hover:border-amber-500 dark:hover:border-amber-500',
      bg: 'hover:bg-amber-50/50 dark:hover:bg-amber-500/5',
      iconBg: 'bg-amber-500/10 group-hover:bg-amber-500/20',
      iconColor: 'text-amber-600 dark:text-amber-400'
    },
    rose: {
      border: 'hover:border-rose-500 dark:hover:border-rose-500',
      bg: 'hover:bg-rose-50/50 dark:hover:bg-rose-500/5',
      iconBg: 'bg-rose-500/10 group-hover:bg-rose-500/20',
      iconColor: 'text-rose-600 dark:text-rose-400'
    },
    indigo: {
      border: 'hover:border-indigo-500 dark:hover:border-indigo-500',
      bg: 'hover:bg-indigo-50/50 dark:hover:bg-indigo-500/5',
      iconBg: 'bg-indigo-500/10 group-hover:bg-indigo-500/20',
      iconColor: 'text-indigo-600 dark:text-indigo-400'
    },
  };

  const classes = colorClasses[color];

  return (
    <button
      onClick={onClick}
      className={`w-full p-4 rounded-xl border-2 border-zinc-200 dark:border-zinc-800 ${classes.border} ${classes.bg} text-left group transition-all`}
    >
      <div className="flex items-start gap-3">
        <div className={`w-10 h-10 rounded-lg ${classes.iconBg} flex items-center justify-center shrink-0 transition-colors`}>
          <div className={`${classes.iconColor} w-5 h-5`}>{icon}</div>
        </div>
        <div className="flex-1">
          <div className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mb-0.5">{title}</div>
          <div className="text-xs text-zinc-500 dark:text-zinc-400">{description}</div>
        </div>
      </div>
    </button>
  );
}
