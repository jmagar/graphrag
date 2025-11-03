"use client";

import { useState, useEffect } from 'react';
import { LeftSidebar } from './LeftSidebar';
import { RightSidebar } from './RightSidebar';
import { SidebarDrawer } from './SidebarDrawer';
import { ChatHeader } from '@/components/chat/ChatHeader';
import { AIMessage } from '@/components/chat/AIMessage';
import { UserMessage } from '@/components/chat/UserMessage';
import { ChatInput } from '@/components/input/ChatInput';
import { Loader } from '@/components/ui/loader';
import { Avatar } from '@/components/chat/Avatar';
import { ScrollButton } from '@/components/ui/scroll-button';
import { SystemMessage } from '@/components/ui/system-message';
import { ChatContainerRoot, ChatContainerContent, ChatContainerScrollAnchor } from '@/components/ui/chat-container';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { useSystemStatus } from '@/hooks/useSystemStatus';
import { toast, Toaster } from 'sonner';

// Type definition for ChatMessage (same as page.tsx)
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string | string[] | ContentSegment[];
  citations?: Array<{ number: number; title: string }>;
  timestamp: string;
  isStreaming?: boolean;
  artifact?: {
    type: 'markdown' | 'code' | 'text' | 'json' | 'html';
    content: string;
    language?: string;
    title?: string;
    url?: string;
  };
  metadata?: {
    url?: string;
    scrapedContent?: string;
  };
  toolCalls?: Array<{
    command: string;
    args?: string;
  }>;
  crawl?: {
    jobId: string;
    status: 'active' | 'completed' | 'failed';
    url: string;
    data?: {
      completed: number;
      total: number;
      creditsUsed: number;
      expiresAt?: string;
      recentPages?: Array<{ url: string; status: string }>;
    };
  };
}

export type ContentSegment =
  | { type: 'text'; text: string }
  | { type: 'tool'; command: string; args?: string; status?: 'running' | 'complete' | 'error' };

interface ClientLayoutProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSendMessage: (content: string) => void;
  onCommand: (command: string, args: string) => void;
  onCancelCrawl: (jobId: string) => Promise<void>;
  leftDrawerOpen: boolean;
  rightDrawerOpen: boolean;
  onLeftDrawerChange: (open: boolean) => void;
  onRightDrawerChange: (open: boolean) => void;
}

export function ClientLayout({
  messages,
  isLoading,
  onSendMessage,
  onCommand,
  onCancelCrawl,
  leftDrawerOpen,
  rightDrawerOpen,
  onLeftDrawerChange,
  onRightDrawerChange
}: ClientLayoutProps) {
  // Use media query to determine if desktop
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  
  // System status management for showing info/warning/error banners
  const { statuses, dismissStatus } = useSystemStatus();
  
  // State to track if hydration is complete
  const [mounted, setMounted] = useState(false);

  // Set mounted flag after first render (after hydration completes)
  useEffect(() => {
    // This is intentional - we need to detect client-side hydration
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  // Only render responsive layout after hydration is complete
  // This prevents server/client mismatch
  if (!mounted) {
    // Render minimal placeholder during SSR - will be hydrated client-side
    return (
      <div className="flex h-screen overflow-hidden bg-zinc-50 dark:bg-zinc-950">
        <div className="flex-1 flex flex-col bg-zinc-50 dark:bg-zinc-900">
          <ChatHeader
            onLeftMenuClick={() => onLeftDrawerChange(true)}
            onRightMenuClick={() => onRightDrawerChange(true)}
            messages={messages.map(m => ({
              id: m.id,
              role: m.role,
              content: Array.isArray(m.content)
                ? m.content.map(c => typeof c === 'string' ? c : c.type === 'text' ? c.text : '')
                : m.content,
              timestamp: m.timestamp,
              citations: m.citations
            }))}
          />
          <ChatContainerRoot className="flex-1 pb-24 md:pb-32">
            <ChatContainerContent className="max-w-3xl mx-auto px-4 md:px-6 py-6 md:py-12 space-y-4 md:space-y-6">
              {messages.map((message) =>
                message.role === 'assistant' ? (
                  <AIMessage
                    key={message.id}
                    content={Array.isArray(message.content) ? message.content : [message.content]}
                    citations={message.citations}
                    timestamp={message.timestamp}
                    isStreaming={message.isStreaming}
                    artifact={message.artifact}
                    toolCalls={message.toolCalls}
                    crawl={message.crawl}
                    onCancelCrawl={onCancelCrawl}
                  />
                ) : (
                  <UserMessage
                    key={message.id}
                    content={message.content as string}
                    timestamp={message.timestamp}
                  />
                )
              )}
              {isLoading && !messages.some(m => m.isStreaming) && (
                <div className="message-animate flex gap-4">
                  <Avatar type="ai" />
                  <div className="flex items-center gap-2 pt-2">
                    <Loader variant="typing" size="md" />
                    <span className="text-sm text-zinc-500 dark:text-zinc-400">Thinking...</span>
                  </div>
                </div>
              )}
              <ChatContainerScrollAnchor />
            </ChatContainerContent>
          </ChatContainerRoot>
          <ChatInput onSend={onSendMessage} />
        </div>
        <Toaster position="top-right" richColors />
      </div>
    );
  }

  // After hydration, render responsive layout based on media query
  return (
    <div className="flex h-screen overflow-hidden bg-zinc-50 dark:bg-zinc-950">
      {/* Left Sidebar - Desktop Only */}
      {isDesktop && <LeftSidebar />}

      {/* Left Drawer - Mobile/Tablet */}
      <SidebarDrawer
        isOpen={leftDrawerOpen}
        onClose={() => onLeftDrawerChange(false)}
        side="left"
      >
        <LeftSidebar />
      </SidebarDrawer>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-zinc-50 dark:bg-zinc-900">
        <ChatHeader
          onLeftMenuClick={() => onLeftDrawerChange(true)}
          onRightMenuClick={() => onRightDrawerChange(true)}
          messages={messages.map(m => ({
            id: m.id,
            role: m.role,
            content: Array.isArray(m.content)
              ? m.content.map(c => typeof c === 'string' ? c : c.type === 'text' ? c.text : '')
              : m.content,
            timestamp: m.timestamp,
            citations: m.citations
          }))}
        />

        {/* System Status Messages */}
        {statuses.length > 0 && (
          <div className="border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50 px-4 md:px-6 py-3 space-y-2">
            {statuses.map((status) => (
              <SystemMessage
                key={status.id}
                variant={status.type === 'error' ? 'error' : status.type === 'warning' ? 'warning' : 'action'}
                fill
                cta={status.cta || (status.dismissible ? {
                  label: 'Dismiss',
                  onClick: () => dismissStatus(status.id)
                } : undefined)}
              >
                {status.message}
              </SystemMessage>
            ))}
          </div>
        )}

        {/* Messages - wrapped with ChatContainer for scroll-to-bottom context */}
        <ChatContainerRoot className="flex-1 pb-24 md:pb-32 relative">
          <ChatContainerContent className="max-w-3xl mx-auto px-4 md:px-6 py-6 md:py-12 space-y-4 md:space-y-6">
            {messages.map((message) =>
              message.role === 'assistant' ? (
                <AIMessage
                  key={message.id}
                  content={Array.isArray(message.content) ? message.content : [message.content]}
                  citations={message.citations}
                  timestamp={message.timestamp}
                  isStreaming={message.isStreaming}
                  artifact={message.artifact}
                  toolCalls={message.toolCalls}
                  crawl={message.crawl}
                  onCancelCrawl={onCancelCrawl}
                />
              ) : (
                <UserMessage
                  key={message.id}
                  content={message.content as string}
                  timestamp={message.timestamp}
                />
              )
            )}

            {/* Typing Indicator - only show when loading but no streaming message exists */}
            {isLoading && !messages.some(m => m.isStreaming) && (
              <div className="message-animate flex gap-4">
                <Avatar type="ai" />
                <div className="flex items-center gap-2 pt-2">
                  <Loader variant="typing" size="md" />
                  <span className="text-sm text-zinc-500 dark:text-zinc-400">Thinking...</span>
                </div>
              </div>
            )}

            {/* Scroll anchor for auto-scroll behavior */}
            <ChatContainerScrollAnchor />
          </ChatContainerContent>

          {/* Floating Scroll-to-Bottom Button */}
          <div className="fixed bottom-32 md:bottom-40 right-6 md:right-8 z-40">
            <ScrollButton />
          </div>
        </ChatContainerRoot>

        {/* Input Area */}
        <ChatInput onSend={onSendMessage} />
      </div>

      {/* Right Sidebar - Desktop Only */}
      {isDesktop && <RightSidebar />}

      {/* Right Drawer - Mobile/Tablet */}
      <SidebarDrawer
        isOpen={rightDrawerOpen}
        onClose={() => onRightDrawerChange(false)}
        side="right"
      >
        <RightSidebar />
      </SidebarDrawer>

      {/* Toast Notifications */}
      <Toaster position="top-right" richColors />
    </div>
  );
}
