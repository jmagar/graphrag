interface CommandItemProps {
  command: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  selected?: boolean;
  onClick: () => void;
}

export function CommandItem({ command, description, icon, color, selected = false, onClick }: CommandItemProps) {
  return (
    <button
      onClick={onClick}
      className={`command-item w-full px-2.5 py-1.5 hover:bg-zinc-50 dark:hover:bg-zinc-800 text-left flex items-center gap-2 rounded-md transition-colors ${selected ? 'selected' : ''}`}
    >
      <div className={`w-6 h-6 rounded bg-${color}-500/10 flex items-center justify-center shrink-0`}>
        <div className={`text-${color}-600 dark:text-${color}-400`}>{icon}</div>
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-xs font-medium text-zinc-900 dark:text-zinc-100">{command}</div>
        <div className="text-[10px] text-zinc-500">{description}</div>
      </div>
    </button>
  );
}
