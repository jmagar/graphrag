"use client";

import { useState, useRef, useEffect } from 'react';

interface Tab {
  id: string;
  label: string;
  dropdownItems?: Array<{ icon: React.ReactNode; title: string; desc: string; color: string }>;
}

const tabs: Tab[] = [
  {
    id: 'chat',
    label: 'Chat',
    dropdownItems: [
      {
        icon: (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
          </svg>
        ),
        title: 'New Chat',
        desc: 'Start a new conversation',
        color: 'blue'
      },
      {
        icon: (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        ),
        title: 'Recent Chats',
        desc: 'View chat history',
        color: 'slate'
      }
    ]
  },
  {
    id: 'sources',
    label: 'Sources',
    dropdownItems: [
      {
        icon: (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4"/>
          </svg>
        ),
        title: 'Add Source',
        desc: 'Upload new document',
        color: 'emerald'
      },
      {
        icon: (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/>
          </svg>
        ),
        title: 'Connect URL',
        desc: 'Add web content',
        color: 'cyan'
      }
    ]
  },
  {
    id: 'graph',
    label: 'Graph',
    dropdownItems: [
      {
        icon: (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/>
          </svg>
        ),
        title: 'View Graph',
        desc: 'Explore knowledge graph',
        color: 'purple'
      },
      {
        icon: (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
          </svg>
        ),
        title: 'Search Nodes',
        desc: 'Find connections',
        color: 'indigo'
      }
    ]
  },
  {
    id: 'pins',
    label: 'Pins',
    dropdownItems: [
      {
        icon: (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"/>
          </svg>
        ),
        title: 'Pinned Items',
        desc: 'View saved content',
        color: 'amber'
      },
      {
        icon: (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/>
          </svg>
        ),
        title: 'Favorites',
        desc: 'Quick access items',
        color: 'yellow'
      }
    ]
  },
  {
    id: 'composer',
    label: 'Composer',
    dropdownItems: [
      {
        icon: (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
          </svg>
        ),
        title: 'New Document',
        desc: 'Create new content',
        color: 'rose'
      },
      {
        icon: (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
        ),
        title: 'Templates',
        desc: 'Use document templates',
        color: 'violet'
      },
      {
        icon: (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"/>
          </svg>
        ),
        title: 'Rich Editor',
        desc: 'Advanced formatting',
        color: 'pink'
      }
    ]
  },
  {
    id: 'explore',
    label: 'Explore',
    dropdownItems: [
      {
        icon: (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        ),
        title: 'Discover',
        desc: 'Find related content',
        color: 'teal'
      },
      {
        icon: (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
          </svg>
        ),
        title: 'Deep Dive',
        desc: 'Detailed analysis',
        color: 'sky'
      }
    ]
  }
];

export function ConversationTabs() {
  const [activeTab, setActiveTab] = useState('chat');
  const [dropdownTab, setDropdownTab] = useState<string | null>(null);
  const [dropdownLeft, setDropdownLeft] = useState(0);
  const tabRefs = useRef<{ [key: string]: HTMLButtonElement | null }>({});
  const containerRef = useRef<HTMLDivElement>(null);

  const handleTabClick = (tabId: string, event: React.MouseEvent<HTMLButtonElement>) => {
    if (activeTab === tabId && dropdownTab === tabId) {
      setDropdownTab(null);
    } else {
      setActiveTab(tabId);
      const button = event.currentTarget;
      const container = containerRef.current;
      if (button && container) {
        const buttonRect = button.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        setDropdownLeft(buttonRect.left - containerRect.left);
      }
      setDropdownTab(tabId);
    }
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest('.conv-tab') && !target.closest('#tabDropdown')) {
        setDropdownTab(null);
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  const currentDropdownItems = tabs.find(t => t.id === dropdownTab)?.dropdownItems || [];

  return (
    <div className="flex items-center gap-1 ml-2 relative" ref={containerRef}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          ref={(el) => { tabRefs.current[tab.id] = el; }}
          onClick={(e) => handleTabClick(tab.id, e)}
          className={`conv-tab px-2.5 py-1 rounded-md text-xs font-medium flex items-center gap-1 transition-colors ${
            activeTab === tab.id
              ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-500/10'
              : 'text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-900'
          }`}
        >
          {tab.label}
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"/>
          </svg>
        </button>
      ))}
      
      {dropdownTab && (
        <div
          id="tabDropdown"
          className="absolute top-full mt-1 w-64 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg shadow-xl overflow-hidden z-50"
          style={{ left: `${dropdownLeft}px` }}
        >
          <div className="tab-dropdown overflow-y-auto custom-scroll p-1 max-h-[300px]">
            {currentDropdownItems.map((item, index) => {
              const colorClasses = {
                blue: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
                slate: 'bg-slate-500/10 text-slate-600 dark:text-slate-400',
                emerald: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
                cyan: 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400',
                purple: 'bg-purple-500/10 text-purple-600 dark:text-purple-400',
                indigo: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400',
                amber: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
                yellow: 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400',
                rose: 'bg-rose-500/10 text-rose-600 dark:text-rose-400',
                violet: 'bg-violet-500/10 text-violet-600 dark:text-violet-400',
                pink: 'bg-pink-500/10 text-pink-600 dark:text-pink-400',
                teal: 'bg-teal-500/10 text-teal-600 dark:text-teal-400',
                sky: 'bg-sky-500/10 text-sky-600 dark:text-sky-400'
              };

              const colorClass = colorClasses[item.color as keyof typeof colorClasses] || colorClasses.blue;

              return (
                <button
                  key={index}
                  className="w-full px-2.5 py-1.5 hover:bg-zinc-50 dark:hover:bg-zinc-800 text-left flex items-center gap-2 rounded-md transition-colors"
                >
                  <div className={`w-6 h-6 rounded flex items-center justify-center shrink-0 ${colorClass}`}>
                    {item.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-zinc-900 dark:text-zinc-100">{item.title}</div>
                    <div className="text-[10px] text-zinc-500">{item.desc}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
