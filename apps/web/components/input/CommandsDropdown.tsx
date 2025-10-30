"use client";

import { CommandItem } from './CommandItem';

interface Command {
  command: string;
  description: string;
  icon: React.ReactNode;
  color: string;
}

interface CommandsDropdownProps {
  selectedIndex: number;
  onSelect: (command: string) => void;
  onHover: (index: number) => void;
  filteredCommands?: string[];
}

const allCommands: Command[] = [
  {
    command: '/scrape',
    description: 'Scrape a single URL',
    color: 'blue',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
      </svg>
    ),
  },
  {
    command: '/crawl',
    description: 'Crawl entire website',
    color: 'amber',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/>
      </svg>
    ),
  },
  {
    command: '/map',
    description: 'Map all URLs on site',
    color: 'emerald',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
      </svg>
    ),
  },
  {
    command: '/search',
    description: 'Search the web',
    color: 'cyan',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
      </svg>
    ),
  },
  {
    command: '/extract',
    description: 'Extract structured data',
    color: 'purple',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/>
      </svg>
    ),
  },
];

export function CommandsDropdown({ selectedIndex, onSelect, onHover, filteredCommands }: CommandsDropdownProps) {
  // Filter commands based on the provided list
  const commandsToShow = filteredCommands 
    ? allCommands.filter(cmd => filteredCommands.includes(cmd.command))
    : allCommands;

  return (
    <div className="absolute bottom-full left-0 mb-2 w-64 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg shadow-xl overflow-hidden">
      <div className="p-1.5 border-b border-zinc-200 dark:border-zinc-800">
        <div className="text-[10px] font-semibold text-zinc-400 px-2 py-1 uppercase tracking-wider">
          Commands {filteredCommands && filteredCommands.length < allCommands.length && (
            <span className="text-blue-500">({commandsToShow.length})</span>
          )}
        </div>
      </div>
      <div className="commands-dropdown overflow-y-auto custom-scroll p-1 max-h-[300px]">
        {commandsToShow.length > 0 ? (
          commandsToShow.map((cmd, index) => (
            <div key={cmd.command} onMouseEnter={() => onHover(index)}>
              <CommandItem
                command={cmd.command}
                description={cmd.description}
                icon={cmd.icon}
                color={cmd.color}
                selected={selectedIndex === index}
                onClick={() => onSelect(cmd.command)}
              />
            </div>
          ))
        ) : (
          <div className="px-3 py-6 text-center text-sm text-zinc-500">
            No matching commands
          </div>
        )}
      </div>
    </div>
  );
}
