// DEPRECATED: This file is no longer used
// Migrated to prompt-kit Source component on 2025-10-30
// See: components/ui/source.tsx
// 
// Old usage:
//   <Citation number={1} title="Example" url="..." preview="..." />
//
// New usage:
//   <Source href="...">
//     <SourceTrigger label={1} showFavicon={false} />
//     <SourceContent title="Example" description="..." />
//   </Source>
//
// This component is kept for backward compatibility with tests
// Migration to Source provides better accessibility and features

import { Source, SourceTrigger, SourceContent } from '@/components/ui/source';

interface CitationProps {
  number: number;
  title: string;
  url?: string;
  preview?: string;
  onClick?: () => void;
}

// Wrapper component for backward compatibility
export function Citation({ number, title, url, preview }: CitationProps) {
  return (
    <Source href={url || '#'}>
      <SourceTrigger 
        label={number} 
        showFavicon={false}
        className="bg-gradient-to-r from-emerald-50 to-emerald-100/50 dark:from-emerald-500/10 dark:to-emerald-500/5 hover:from-emerald-100 hover:to-emerald-100 dark:hover:from-emerald-500/20 dark:hover:to-emerald-500/10 border-emerald-200/50 dark:border-emerald-500/20 text-emerald-900 dark:text-emerald-300"
      />
      {url && (
        <SourceContent 
          title={title}
          description={preview || `Source ${number}`}
        />
      )}
    </Source>
  );
}
