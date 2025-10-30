export function StatisticsSection() {
  return (
    <div className="p-4 border-b border-zinc-200 dark:border-zinc-800/80">
      <div className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">Statistics</div>
      <div className="space-y-1">
        <div className="flex items-center justify-between py-1 text-xs">
          <span className="text-zinc-600 dark:text-zinc-400">Documents</span>
          <span className="font-semibold text-zinc-900 dark:text-zinc-100">1,247</span>
        </div>
        <div className="flex items-center justify-between py-1 text-xs">
          <span className="text-zinc-600 dark:text-zinc-400">Vectors</span>
          <span className="font-semibold text-zinc-900 dark:text-zinc-100">45.2K</span>
        </div>
        <div className="flex items-center justify-between py-1 text-xs">
          <span className="text-zinc-600 dark:text-zinc-400">Storage</span>
          <span className="font-semibold text-zinc-900 dark:text-zinc-100">2.4 GB</span>
        </div>
      </div>
    </div>
  );
}
