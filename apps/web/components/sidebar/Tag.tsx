interface TagProps {
  label: string;
  color: 'blue' | 'emerald' | 'purple' | 'amber' | 'cyan' | 'rose' | 'indigo' | 'teal';
  size?: 'xs' | 'sm' | 'md';
  onClick?: () => void;
}

export function Tag({ label, color, size = 'sm', onClick }: TagProps) {
  const colorClasses = {
    blue: 'bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-500/20',
    emerald: 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-100 dark:hover:bg-emerald-500/20',
    purple: 'bg-purple-50 dark:bg-purple-500/10 text-purple-700 dark:text-purple-400 hover:bg-purple-100 dark:hover:bg-purple-500/20',
    amber: 'bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 hover:bg-amber-100 dark:hover:bg-amber-500/20',
    cyan: 'bg-cyan-50 dark:bg-cyan-500/10 text-cyan-700 dark:text-cyan-400 hover:bg-cyan-100 dark:hover:bg-cyan-500/20',
    rose: 'bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-400 hover:bg-rose-100 dark:hover:bg-rose-500/20',
    indigo: 'bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-500/20',
    teal: 'bg-teal-50 dark:bg-teal-500/10 text-teal-700 dark:text-teal-400 hover:bg-teal-100 dark:hover:bg-teal-500/20',
  };

  const sizeClasses = {
    xs: 'px-2 py-0.5 text-[10px]',
    sm: 'px-2 py-0.5 text-[11px]',
    md: 'px-2.5 py-1 text-xs',
  };

  return (
    <span
      onClick={onClick}
      className={`rounded-md font-medium cursor-pointer transition-colors ${colorClasses[color]} ${sizeClasses[size]}`}
    >
      {label}
    </span>
  );
}
