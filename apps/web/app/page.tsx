"use client";

import { useState, useRef, useEffect } from 'react';
import { LeftSidebar } from '@/components/layout/LeftSidebar';
import { RightSidebar } from '@/components/layout/RightSidebar';
import { SidebarDrawer } from '@/components/layout/SidebarDrawer';
import { ChatHeader } from '@/components/chat/ChatHeader';
import { AIMessage } from '@/components/chat/AIMessage';
import { UserMessage } from '@/components/chat/UserMessage';
import { ChatInput } from '@/components/input/ChatInput';
import { TypingIndicator } from '@/components/chat/TypingIndicator';
import { useIsDesktop } from '@/hooks/useMediaQuery';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string | string[];
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

export default function GraphRAGPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [leftDrawerOpen, setLeftDrawerOpen] = useState(false);
  const [rightDrawerOpen, setRightDrawerOpen] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null); // Claude Agent SDK session
  const abortControllerRef = useRef<AbortController | null>(null);
  const messageTimestampsRef = useRef<number[]>([]);
  const isDesktop = useIsDesktop();

  // Real-time crawl progress polling
  useEffect(() => {
    const activeCrawls = messages.filter(m => m.crawl?.status === 'active');
    if (activeCrawls.length === 0) return;

    const intervals: NodeJS.Timeout[] = [];

    activeCrawls.forEach((message) => {
      if (!message.crawl) return;
      
      const { jobId } = message.crawl;
      
      const pollStatus = async () => {
        try {
          const response = await fetch(`/api/crawl/status/${jobId}`);
          if (!response.ok) return;
          
          const statusData = await response.json();
          const status = statusData.status;
          const isComplete = status === 'completed' || status === 'failed';
          
          // Extract recent pages
          const recentPages = statusData.data && statusData.data.length > 0
            ? statusData.data.slice(-5).map((p: any) => ({
                url: p.metadata?.sourceURL || 'Unknown',
                status: 'completed'
              }))
            : [];

          // Update message with structured data
          setMessages(prev => prev.map(m => 
            m.id === message.id
              ? {
                  ...m,
                  crawl: {
                    ...m.crawl!,
                    status: isComplete ? (status === 'completed' ? 'completed' : 'failed') : 'active',
                    data: {
                      completed: statusData.completed || 0,
                      total: statusData.total || 0,
                      creditsUsed: statusData.creditsUsed || 0,
                      expiresAt: statusData.expiresAt,
                      recentPages
                    }
                  }
                }
              : m
          ));
          
        } catch (error) {
          console.error('Failed to poll crawl status:', error);
        }
      };

      // Poll immediately, then every 3 seconds
      pollStatus();
      const interval = setInterval(pollStatus, 3000);
      intervals.push(interval);
    });

    // Cleanup
    return () => {
      intervals.forEach(interval => clearInterval(interval));
    };
  }, [messages]);

  const handleCommand = async (command: string, args: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: `/${command} ${args}`,
      timestamp: new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      let result: string;
      let artifactType: 'markdown' | 'json' | 'text' = 'markdown';
      let artifactTitle = '';

      switch (command.toLowerCase()) {
        case 'scrape': {
          const urlArg = args.trim();
          if (!urlArg) {
            throw new Error('Usage: /scrape <url>\nExample: /scrape https://react.dev');
          }
          
          // Auto-add https:// if missing
          const url = urlArg.startsWith('http') ? urlArg : `https://${urlArg}`;
          
          const response = await fetch('/api/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, formats: ['markdown'] })
          });
          
          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Scrape failed');
          }
          const data = await response.json();
          result = data.data?.markdown || 'Scraped successfully';
          artifactTitle = 'Scraped Content';
          
          // Store scraped content in message metadata so assistant can access it
          const responseMessage: Message = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: [`✅ Scraped content from URL. You can ask me questions about it!`],
            timestamp: new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }),
            artifact: {
              type: artifactType,
              content: result,
              title: artifactTitle,
              url: args.trim()
            },
            metadata: {
              url: args.trim(),
              scrapedContent: result
            },
            toolCalls: [{
              command: 'scrape',
              args: args.trim()
            }]
          };
          setMessages(prev => [...prev, responseMessage]);
          setIsLoading(false);
          return; // Early return for scrape command
        }

        case 'map': {
          if (!args.trim()) {
            throw new Error('Usage: /map <url>');
          }
          const response = await fetch('/api/map', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: args.trim(), limit: 100 })
          });
          if (!response.ok) throw new Error('Map failed');
          const data = await response.json();
          result = `Found ${data.total} URLs:\n\n${data.urls.join('\n')}`;
          artifactType = 'text';
          artifactTitle = 'Website Map';
          break;
        }

        case 'search': {
          if (!args.trim()) {
            throw new Error('Usage: /search <query>');
          }
          const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: args.trim(), limit: 5 })
          });
          if (!response.ok) throw new Error('Search failed');
          const data = await response.json();
          const fullResults = data.results.map((r: any, i: number) => 
            `### ${i + 1}. ${r.title}\n**URL**: ${r.url}\n\n${r.content}\n`
          ).join('\n---\n\n');
          result = data.results.map((r: any, i: number) => 
            `### ${i + 1}. ${r.title}\n**URL**: ${r.url}\n\n${r.content.substring(0, 300)}...\n`
          ).join('\n---\n\n');
          artifactTitle = 'Search Results';
          
          // Store full search results in metadata for assistant context
          const responseMessage: Message = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: [`✅ Search completed. You can ask me questions about these results!`],
            timestamp: new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }),
            artifact: {
              type: artifactType,
              content: result,
              title: artifactTitle
            },
            metadata: {
              scrapedContent: fullResults // Store full content for context
            },
            toolCalls: [{
              command: 'search',
              args: args.trim()
            }]
          };
          setMessages(prev => [...prev, responseMessage]);
          setIsLoading(false);
          return;
        }

        case 'extract': {
          const trimmedArgs = args.trim();
          if (!trimmedArgs) {
            throw new Error('Usage: /extract <url> <what to extract>\nExample: /extract https://news.ycombinator.com article titles and scores');
          }
          
          // Match URL and schema description (more flexible regex)
          const urlMatch = trimmedArgs.match(/^(\S+)\s+(.+)$/);
          if (!urlMatch) {
            throw new Error('Usage: /extract <url> <what to extract>\nExample: /extract https://news.ycombinator.com article titles and scores');
          }
          
          const [, urlArg, schemaDesc] = urlMatch;
          
          // Auto-add https:// if missing
          const url = urlArg.startsWith('http') ? urlArg : `https://${urlArg}`;
          const response = await fetch('/api/extract', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              url,
              schema: { extract: schemaDesc }
            })
          });
          if (!response.ok) throw new Error('Extract failed');
          const data = await response.json();
          result = JSON.stringify(data.data, null, 2);
          artifactType = 'json';
          artifactTitle = 'Extracted Data';
          
          // Store extracted data in metadata for assistant context
          const responseMessage: Message = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: [`✅ Data extracted. You can ask me questions about this data!`],
            timestamp: new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }),
            artifact: {
              type: artifactType,
              content: result,
              title: artifactTitle,
              url
            },
            metadata: {
              url,
              scrapedContent: `Extracted from ${url}:\n${result}`
            },
            toolCalls: [{
              command: 'extract',
              args: `${url} ${schemaDesc}`.trim()
            }]
          };
          setMessages(prev => [...prev, responseMessage]);
          setIsLoading(false);
          return;
        }

        case 'map': {
          const urlArg = args.trim();
          if (!urlArg) {
            throw new Error('Usage: /map <url>\nExample: /map https://react.dev');
          }
          
          // Auto-add https:// if missing
          const url = urlArg.startsWith('http') ? urlArg : `https://${urlArg}`;
          
          const response = await fetch('/api/map', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, limit: 100 })
          });
          
          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Map failed');
          }
          
          const data = await response.json();
          result = `Found ${data.total} URLs:\n\n${data.urls.join('\n')}`;
          artifactType = 'text';
          artifactTitle = 'Website Map';
          
          // Map results - show as artifact (no need for context)
          const responseMessage: Message = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: [`✅ Mapped ${data.total} URLs from the website`],
            timestamp: new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }),
            artifact: {
              type: artifactType,
              content: result,
              title: artifactTitle
            },
            toolCalls: [{
              command: 'map',
              args: url
            }]
          };
          setMessages(prev => [...prev, responseMessage]);
          setIsLoading(false);
          return;
        }

        case 'crawl': {
          const urlArg = args.trim();
          if (!urlArg) {
            throw new Error('Usage: /crawl <url>\nExample: /crawl https://docs.react.dev');
          }
          
          // Auto-add https:// if missing
          const url = urlArg.startsWith('http') ? urlArg : `https://${urlArg}`;
          
          const response = await fetch('/api/crawl', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, maxDepth: 2, maxPages: 10 })
          });
          
          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Crawl failed');
          }
          
          const data = await response.json();
          const jobId = data.id || data.jobId;
          
          // Fetch detailed status immediately to get initial data
          const statusResponse = await fetch(`/api/crawl/status/${jobId}`);
          const statusData = statusResponse.ok ? await statusResponse.json() : null;
          
          // Extract recent pages for initial render
          const recentPages = statusData?.data && statusData.data.length > 0
            ? statusData.data.slice(-5).map((p: any) => ({
                url: p.metadata?.sourceURL || 'Unknown',
                status: 'completed'
              }))
            : [];
          
          // Crawl status - use CrawlProgress component (no artifact)
          const responseMessage: Message = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: [`✅ Crawl job started! Watch the progress update in real-time below.`],
            timestamp: new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }),
            crawl: {
              jobId,
              status: 'active',
              url,
              data: {
                completed: statusData?.completed || 0,
                total: statusData?.total || 0,
                creditsUsed: statusData?.creditsUsed || 0,
                expiresAt: statusData?.expiresAt,
                recentPages
              }
            }
          };
          setMessages(prev => [...prev, responseMessage]);
          setIsLoading(false);
          return;
        }

        default:
          throw new Error(`Unknown command: /${command}\n\nAvailable: /scrape, /crawl, /map, /search, /extract`);
      }
      
    } catch (error: any) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `❌ ${error.message}`,
        timestamp: new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancelCrawl = async (jobId: string) => {
    try {
      const response = await fetch(`/api/crawl/${jobId}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        console.error('Failed to cancel crawl');
        return;
      }
      
      // Update message to show cancelled status
      setMessages(prev => prev.map(m => 
        m.crawl?.jobId === jobId
          ? {
              ...m,
              crawl: {
                ...m.crawl,
                status: 'failed'
              }
            }
          : m
      ));
    } catch (error) {
      console.error('Failed to cancel crawl:', error);
    }
  };

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return;

    // RATE LIMITING: Max 5 messages per minute
    const now = Date.now();
    const oneMinuteAgo = now - 60000;
    
    // Remove timestamps older than 1 minute
    messageTimestampsRef.current = messageTimestampsRef.current.filter(ts => ts > oneMinuteAgo);
    
    // Check if user has sent 5 messages in the last minute
    if (messageTimestampsRef.current.length >= 5) {
      alert('Rate limit: You can only send 5 messages per minute. Please wait.');
      return;
    }
    
    // Add current timestamp
    messageTimestampsRef.current.push(now);

    // COMMAND DETECTION: Check for slash commands first
    const commandRegex = /^\/(\w+)\s*(.*)$/;
    const commandMatch = content.trim().match(commandRegex);
    
    if (commandMatch) {
      const [, command, args] = commandMatch;
      await handleCommand(command, args);
      return;
    }

    // Detect if message is just a URL
    const urlRegex = /^https?:\/\/.+$/i;
    const isUrl = urlRegex.test(content.trim());

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    // If it's a URL, scrape it first
    if (isUrl) {
      try {
        const scrapeResponse = await fetch('/api/scrape', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            url: content.trim(),
            formats: ['markdown', 'html']
          })
        });

        if (!scrapeResponse.ok) {
          throw new Error('Failed to scrape URL');
        }

        const scrapeData = await scrapeResponse.json();
        
        // Add scraped content as an artifact
        const markdown = scrapeData.data?.markdown || scrapeData.data?.html || 'Content retrieved successfully';
        const scrapeMessage: Message = {
          id: (Date.now() + 0.5).toString(),
          role: 'assistant',
          content: [`I've scraped the content from this URL. You can ask me questions about it!`],
          timestamp: new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }),
          artifact: {
            type: 'markdown',
            content: markdown,
            title: 'Scraped Content',
            url: content.trim()
          },
          metadata: {
            url: content.trim(),
            scrapedContent: markdown
          }
        };
        setMessages(prev => [...prev, scrapeMessage]);
        setIsLoading(false);
        return;
      } catch (scrapeError: any) {
        console.error('Scrape error:', scrapeError);
        // Show error message
        const errorMessage: Message = {
          id: (Date.now() + 0.5).toString(),
          role: 'assistant',
          content: `❌ Failed to scrape URL: ${scrapeError.message}`,
          timestamp: new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
        };
        setMessages(prev => [...prev, errorMessage]);
        setIsLoading(false);
        return;
      }
    }

    // Create assistant message placeholder for streaming
    const assistantId = (Date.now() + 1).toString();
    const assistantMessage: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }),
      isStreaming: true,
      toolCalls: [] // Initialize empty tool calls array
    };
    setMessages(prev => [...prev, assistantMessage]);

    try {
      // Create abort controller for this request
      abortControllerRef.current = new AbortController();

      // Send message with session ID (if exists) for conversation continuity
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: content,
          sessionId // SDK handles conversation state
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedContent = '';
      const toolsInUse = new Map<string, { name: string; input: string }>(); // Track tool calls by ID

      if (!reader) {
        throw new Error('No response body');
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (!line.trim() || !line.startsWith('data: ')) continue;
          
          const data = line.slice(6); // Remove 'data: ' prefix
          if (data === '[DONE]') {
            setIsLoading(false);
            setMessages(prev => 
              prev.map(m => m.id === assistantId 
                ? { ...m, isStreaming: false }
                : m
              )
            );
            continue;
          }

          try {
            const parsed = JSON.parse(data);

            // Capture session ID for conversation continuity
            if (parsed.type === 'session_init') {
              setSessionId(parsed.session_id);
              console.log('Session started:', parsed.session_id);
            }

            // Handle different message types from Claude Agent SDK
            // ONLY use stream_event for live updates to avoid duplicates
            if (parsed.type === 'stream_event') {
              const event = parsed.event;
              
              // Tool use started
              if (event?.type === 'content_block_start' && event.content_block?.type === 'tool_use') {
                const toolId = event.content_block.id;
                const toolName = event.content_block.name;
                toolsInUse.set(toolId, { name: toolName, input: '' });
                
                // Update UI immediately to show tool is being used
                setMessages(prev => 
                  prev.map(m => m.id === assistantId 
                    ? { 
                        ...m, 
                        toolCalls: Array.from(toolsInUse.values()).map(t => ({
                          command: t.name,
                          args: t.input
                        }))
                      }
                    : m
                  )
                );
              }
              
              // Tool input streaming (parameters)
              if (event?.type === 'content_block_delta' && event.delta?.type === 'input_json_delta') {
                const toolId = event.index; // Content block index
                const partialJson = event.delta.partial_json;
                
                // Accumulate input JSON
                const toolIds = Array.from(toolsInUse.keys());
                if (toolIds[toolId]) {
                  const tool = toolsInUse.get(toolIds[toolId]);
                  if (tool) {
                    tool.input += partialJson;
                    
                    // Try to parse and format args nicely
                    try {
                      const parsed = JSON.parse(tool.input);
                      const argsStr = Object.entries(parsed)
                        .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
                        .join(', ');
                      
                      setMessages(prev => 
                        prev.map(m => m.id === assistantId 
                          ? { 
                              ...m, 
                              toolCalls: Array.from(toolsInUse.values()).map(t => ({
                                command: t.name,
                                args: t.name === tool.name ? argsStr : t.input
                              }))
                            }
                          : m
                        )
                      );
                    } catch {
                      // JSON not complete yet, keep accumulating
                    }
                  }
                }
              }
              
              // Streaming text response
              if (event?.type === 'content_block_delta' && event.delta?.type === 'text_delta') {
                accumulatedContent += event.delta.text;
                setMessages(prev => 
                  prev.map(m => m.id === assistantId 
                    ? { ...m, content: accumulatedContent }
                    : m
                  )
                );
              }
            } else if (parsed.type === 'result') {
              // Final result
              if (parsed.subtype === 'success' && parsed.result) {
                setMessages(prev => 
                  prev.map(m => m.id === assistantId 
                    ? { ...m, content: accumulatedContent || parsed.result, isStreaming: false }
                    : m
                  )
                );
              }
              setIsLoading(false);
            } else if (parsed.type === 'error') {
              throw new Error(parsed.error || 'Unknown error');
            }
          } catch (parseError) {
            console.error('Error parsing SSE data:', parseError);
          }
        }
      }
    } catch (error: any) {
      console.error('Chat error:', error);
      setIsLoading(false);
      
      // Update assistant message with error
      setMessages(prev => 
        prev.map(m => m.id === assistantId 
          ? { 
              ...m, 
              content: `Error: ${error.message || 'Failed to get response'}`,
              isStreaming: false 
            }
          : m
        )
      );
    } finally {
      abortControllerRef.current = null;
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-zinc-50 dark:bg-zinc-950">
      {/* Left Sidebar - Desktop Only */}
      {isDesktop && <LeftSidebar />}
      
      {/* Left Drawer - Mobile/Tablet */}
      <SidebarDrawer
        isOpen={leftDrawerOpen}
        onClose={() => setLeftDrawerOpen(false)}
        side="left"
      >
        <LeftSidebar />
      </SidebarDrawer>
      
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-zinc-50 dark:bg-zinc-900">
        <ChatHeader 
          onLeftMenuClick={() => setLeftDrawerOpen(true)}
          onRightMenuClick={() => setRightDrawerOpen(true)}
        />
        
        {/* Messages */}
        <div className="flex-1 overflow-y-auto custom-scroll pb-24 md:pb-32">
          <div className="max-w-3xl mx-auto px-4 md:px-6 py-6 md:py-12 space-y-4 md:space-y-6">
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
                  onCancelCrawl={handleCancelCrawl}
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
            {isLoading && !messages.some(m => m.isStreaming) && <TypingIndicator />}
          </div>
        </div>
        
        {/* Input Area */}
        <ChatInput onSend={handleSendMessage} />
      </div>
      
      {/* Right Sidebar - Desktop Only */}
      {isDesktop && <RightSidebar />}
      
      {/* Right Drawer - Mobile/Tablet */}
      <SidebarDrawer
        isOpen={rightDrawerOpen}
        onClose={() => setRightDrawerOpen(false)}
        side="right"
      >
        <RightSidebar />
      </SidebarDrawer>
    </div>
  );
}
