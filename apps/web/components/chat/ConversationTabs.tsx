"use client";

import { useState, useRef, useEffect } from 'react';

interface Tab {
  id: string;
  label: string;
  dropdownItems?: Array<{ icon: string; title: string; desc: string }>;
}

const tabs: Tab[] = [
  {
    id: 'chat',
    label: 'Chat',
    dropdownItems: [
      { icon: '💬', title: 'New Chat', desc: 'Start a new conversation' },
      { icon: '📋', title: 'Recent Chats', desc: 'View chat history' }
    ]
  },
  {
    id: 'sources',
    label: 'Sources',
    dropdownItems: [
      { icon: '📄', title: 'Add Source', desc: 'Upload new document' },
      { icon: '🔗', title: 'Connect URL', desc: 'Add web content' }
    ]
  },
  {
    id: 'graph',
    label: 'Graph',
    dropdownItems: [
      { icon: '🌐', title: 'View Graph', desc: 'Explore knowledge graph' },
      { icon: '🔍', title: 'Search Nodes', desc: 'Find connections' }
    ]
  },
  {
    id: 'pins',
    label: 'Pins',
    dropdownItems: [
      { icon: '📌', title: 'Pinned Items', desc: 'View saved content' },
      { icon: '⭐', title: 'Favorites', desc: 'Quick access items' }
    ]
  },
  {
    id: 'composer',
    label: 'Composer',
    dropdownItems: [
      { icon: '✍️', title: 'New Document', desc: 'Create new content' },
      { icon: '📝', title: 'Templates', desc: 'Use document templates' },
      { icon: '🎨', title: 'Rich Editor', desc: 'Advanced formatting' }
    ]
  },
  {
    id: 'explore',
    label: 'Explore',
    dropdownItems: [
      { icon: '🧭', title: 'Discover', desc: 'Find related content' },
      { icon: '🔎', title: 'Deep Dive', desc: 'Detailed analysis' }
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
          className="absolute top-full mt-1 w-56 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-xl overflow-hidden z-50"
          style={{ left: `${dropdownLeft}px` }}
        >
          <div className="tab-dropdown overflow-y-auto custom-scroll p-1 max-h-[400px]">
            {currentDropdownItems.map((item, index) => (
              <button
                key={index}
                className="w-full px-3 py-2 hover:bg-zinc-50 dark:hover:bg-zinc-800 text-left flex items-center gap-3 rounded-md transition-colors"
              >
                <span className="text-xl">{item.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{item.title}</div>
                  <div className="text-xs text-zinc-500">{item.desc}</div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
