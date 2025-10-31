'use client';

import { useState } from 'react';

// Color class mappings for Tailwind JIT compilation
const colorClasses = {
  blue: 'text-blue-600 dark:text-blue-400',
  purple: 'text-purple-600 dark:text-purple-400',
  green: 'text-green-600 dark:text-green-400'
} as const;

interface Tool {
  name: string;
  description: string;
  params: Array<{ name: string; description: string; required?: boolean }>;
  category: 'web' | 'crawl' | 'search';
}

const AVAILABLE_TOOLS: Tool[] = [
  {
    name: 'scrape_url',
    description: 'Get content from a single webpage in markdown or HTML format',
    category: 'web',
    params: [
      { name: 'url', description: 'The URL to scrape', required: true },
      { name: 'formats', description: 'Content formats to retrieve (markdown, html)', required: false }
    ]
  },
  {
    name: 'map_website',
    description: 'List all URLs found on a website to discover site structure',
    category: 'web',
    params: [
      { name: 'url', description: 'The website URL to map', required: true },
      { name: 'limit', description: 'Maximum number of URLs to return', required: false }
    ]
  },
  {
    name: 'search_web',
    description: 'Search the web and get full page content for results',
    category: 'search',
    params: [
      { name: 'query', description: 'The search query', required: true },
      { name: 'limit', description: 'Number of results to return (1-10)', required: false }
    ]
  },
  {
    name: 'extract_structured_data',
    description: 'Extract specific data fields from a webpage using natural language',
    category: 'web',
    params: [
      { name: 'url', description: 'The URL to extract data from', required: true },
      { name: 'schema_description', description: 'What to extract (e.g., "article titles and dates")', required: true }
    ]
  },
  {
    name: 'start_crawl',
    description: 'Start async crawl job to index entire website into Qdrant knowledge base',
    category: 'crawl',
    params: [
      { name: 'url', description: 'The website URL to crawl', required: true },
      { name: 'max_depth', description: 'Maximum crawl depth (1-5)', required: false },
      { name: 'max_pages', description: 'Maximum pages to crawl (1-100)', required: false }
    ]
  },
  {
    name: 'check_crawl_status',
    description: 'Monitor the progress of a running crawl job',
    category: 'crawl',
    params: [
      { name: 'job_id', description: 'The crawl job ID to check', required: true }
    ]
  },
  {
    name: 'query_knowledge_base',
    description: 'Search previously crawled/indexed content using semantic search',
    category: 'search',
    params: [
      { name: 'query', description: 'The search query', required: true },
      { name: 'limit', description: 'Number of results (1-10)', required: false },
      { name: 'score_threshold', description: 'Minimum similarity score (0-1)', required: false }
    ]
  }
];

const categoryInfo = {
  web: {
    name: 'Web Scraping',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
      </svg>
    ),
    color: 'blue'
  },
  crawl: {
    name: 'Website Crawling',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/>
      </svg>
    ),
    color: 'purple'
  },
  search: {
    name: 'Search',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
      </svg>
    ),
    color: 'green'
  }
};

export function ToolsInfo() {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [expandedTool, setExpandedTool] = useState<string | null>(null);

  const categories = Array.from(new Set(AVAILABLE_TOOLS.map(t => t.category)));
  const filteredTools = selectedCategory 
    ? AVAILABLE_TOOLS.filter(t => t.category === selectedCategory)
    : AVAILABLE_TOOLS;

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
          Available Tools
        </h2>
        <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1">
          AI can use these tools automatically
        </p>
      </div>

      {/* Category Filter */}
      <div className="px-4 py-3 border-b border-zinc-200 dark:border-zinc-800 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setSelectedCategory(null)}
          className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${
            selectedCategory === null
              ? 'bg-zinc-900 dark:bg-zinc-100 text-zinc-100 dark:text-zinc-900'
              : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700'
          }`}
        >
          All ({AVAILABLE_TOOLS.length})
        </button>
        {categories.map(cat => {
          const info = categoryInfo[cat as keyof typeof categoryInfo];
          const count = AVAILABLE_TOOLS.filter(t => t.category === cat).length;
          return (
            <button
              type="button"
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1.5 text-xs rounded-lg transition-colors flex items-center gap-1.5 ${
                selectedCategory === cat
                  ? 'bg-zinc-900 dark:bg-zinc-100 text-zinc-100 dark:text-zinc-900'
                  : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700'
              }`}
            >
              {info.icon}
              {info.name} ({count})
            </button>
          );
        })}
      </div>

      {/* Tools List */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        {filteredTools.map(tool => {
          const isExpanded = expandedTool === tool.name;
          const info = categoryInfo[tool.category];
          
          return (
            <div
              key={tool.name}
              className="border border-zinc-200 dark:border-zinc-800 rounded-lg overflow-hidden"
            >
              <button
                type="button"
                onClick={() => setExpandedTool(isExpanded ? null : tool.name)}
                className="w-full px-3 py-2.5 flex items-start gap-3 hover:bg-zinc-50 dark:hover:bg-zinc-900/50 transition-colors text-left"
              >
                <div className={`flex-shrink-0 mt-0.5 ${colorClasses[info.color as keyof typeof colorClasses]}`}>
                  {info.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <code className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                      {tool.name}
                    </code>
                    <svg
                      aria-hidden="true"
                      className={`w-4 h-4 flex-shrink-0 text-zinc-400 transition-transform ${
                        isExpanded ? 'rotate-180' : ''
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"/>
                    </svg>
                  </div>
                  <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1">
                    {tool.description}
                  </p>
                </div>
              </button>

              {isExpanded && (
                <div className="px-3 py-2.5 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50">
                  <div className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-2">
                    Parameters:
                  </div>
                  <div className="space-y-2">
                    {tool.params.map(param => (
                      <div key={param.name} className="flex items-start gap-2">
                        <code className="text-xs bg-zinc-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded text-zinc-900 dark:text-zinc-100 font-mono">
                          {param.name}
                        </code>
                        {param.required && (
                          <span className="text-xs text-red-600 dark:text-red-400 font-semibold">
                            *
                          </span>
                        )}
                        <span className="text-xs text-zinc-600 dark:text-zinc-400 flex-1">
                          {param.description}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50">
        <div className="flex items-start gap-2">
          <svg className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <p className="text-xs text-zinc-600 dark:text-zinc-400">
            The AI will automatically choose and use these tools based on your requests
          </p>
        </div>
      </div>
    </div>
  );
}
