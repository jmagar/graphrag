"use client";

import { ConversationTabs } from './ConversationTabs';
import { MobileMenu } from '../layout/MobileMenu';

interface ChatHeaderProps {
  onLeftMenuClick?: () => void;
  onRightMenuClick?: () => void;
}

export function ChatHeader({ onLeftMenuClick, onRightMenuClick }: ChatHeaderProps) {
  const handleExport = () => {
    alert('Export functionality - to be implemented');
  };

  const handleShare = () => {
    alert('Share functionality - to be implemented');
  };

  return (
    <div className="border-b border-zinc-200 dark:border-zinc-800/80 bg-white dark:bg-zinc-900">
      <div className="h-14 flex items-center justify-between px-3 md:px-6">
        <div className="flex items-center gap-2 md:gap-4 flex-1 min-w-0">
          {/* Mobile Menu - Left */}
          {onLeftMenuClick && <MobileMenu onClick={onLeftMenuClick} side="left" />}
          
          <div className="flex items-center gap-2 min-w-0 flex-1">
            <h2 className="text-sm font-semibold truncate">GraphRAG Configuration</h2>
            <div className="hidden sm:flex items-center gap-1.5 text-xs text-zinc-500">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
              <span>3 sources</span>
            </div>
          </div>
          
          {/* Hide tabs on mobile to save space */}
          <div className="hidden md:block">
            <ConversationTabs />
          </div>
        </div>
        
        <div className="flex items-center gap-1 md:gap-2">
          <button
            onClick={handleExport}
            className="w-9 h-9 md:w-8 md:h-8 hover:bg-zinc-100 dark:hover:bg-zinc-900 rounded-lg flex items-center justify-center transition-colors active:scale-95"
            title="Export"
          >
            <svg className="w-4 h-4 text-zinc-600 dark:text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
            </svg>
          </button>
          <button
            onClick={handleShare}
            className="w-9 h-9 md:w-8 md:h-8 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-600 text-white rounded-lg flex items-center justify-center transition-all shadow-sm hover:shadow-md active:scale-95"
            title="Share"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"/>
            </svg>
          </button>
          
          {/* Mobile Menu - Right */}
          {onRightMenuClick && <MobileMenu onClick={onRightMenuClick} side="right" />}
        </div>
      </div>
    </div>
  );
}
