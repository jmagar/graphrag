"use client";

import { SidebarHeader } from '../sidebar/SidebarHeader';
import { SpacesSection } from '../sidebar/SpacesSection';
import { TagsSection } from '../sidebar/TagsSection';
import { StatisticsSection } from '../sidebar/StatisticsSection';

export function LeftSidebar() {
  const handleAddSource = () => {
    alert('Add Source functionality - to be implemented');
  };

  return (
    <div className="w-72 border-r border-zinc-200 dark:border-zinc-800/80 bg-white dark:bg-zinc-900 flex flex-col">
      <SidebarHeader onAddSource={handleAddSource} />
      <div className="flex-1 overflow-y-auto custom-scroll">
        <SpacesSection />
        <TagsSection />
        <StatisticsSection />
      </div>
    </div>
  );
}
