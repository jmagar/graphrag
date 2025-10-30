interface InputFooterProps {
  isFocused: boolean;
}

export function InputFooter({ isFocused }: InputFooterProps) {
  if (isFocused) {
    return (
      <>
        <div className="text-xs text-zinc-400">
          Type <kbd className="px-1.5 py-0.5 bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded text-[10px]">@</kbd> to mention sources or <kbd className="px-1.5 py-0.5 bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded text-[10px]">/</kbd> for commands
        </div>
        <div className="flex items-center gap-1 text-xs text-zinc-400">
          <kbd className="px-1.5 py-0.5 bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded text-[10px]">⌘</kbd>
          <span>+</span>
          <kbd className="px-1.5 py-0.5 bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded text-[10px]">Enter</kbd>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="flex items-center gap-1 text-xs text-zinc-400">
        <span>Press</span>
        <kbd className="px-1.5 py-0.5 bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded text-[10px]">⌘</kbd>
        <span>+</span>
        <kbd className="px-1.5 py-0.5 bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded text-[10px]">K</kbd>
        <span>to focus</span>
      </div>
      <div className="text-xs text-zinc-400">&nbsp;</div>
    </>
  );
}
