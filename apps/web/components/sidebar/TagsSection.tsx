import { Tag } from './Tag';

export function TagsSection() {
  return (
    <div className="p-4 border-b border-zinc-200 dark:border-zinc-800/80">
      <div className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">Tags</div>
      <div className="flex flex-wrap gap-2">
        <Tag label="embeddings" color="blue" size="md" />
        <Tag label="qdrant" color="emerald" size="sm" />
        <Tag label="vector-search" color="purple" size="md" />
        <Tag label="api" color="amber" size="xs" />
        <Tag label="configuration" color="cyan" size="md" />
        <Tag label="crawling" color="rose" size="sm" />
        <Tag label="dimensions" color="indigo" size="md" />
        <Tag label="tei" color="teal" size="xs" />
      </div>
    </div>
  );
}
