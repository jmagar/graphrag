"use client";

import { SpaceCard } from './SpaceCard';

export function SpacesSection() {
  return (
    <div className="p-4 border-b border-zinc-200 dark:border-zinc-800/80">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Spaces</span>
      </div>
      <div className="space-y-1.5">
        <SpaceCard
          name="Work"
          sourceCount={247}
          color="blue"
          isActive={true}
          icon={
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
            </svg>
          }
        />
        <SpaceCard
          name="Play"
          sourceCount={89}
          color="emerald"
          icon={
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          }
        />
        <SpaceCard
          name="Dev"
          sourceCount={156}
          color="purple"
          icon={
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>
            </svg>
          }
        />
      </div>
    </div>
  );
}
