"use client";

// Force dynamic rendering to avoid pre-rendering issues with React context
export const dynamic = 'force-dynamic';

import { useState, useRef, useEffect } from 'react';
import { ClientLayout, type ChatMessage, type ContentSegment } from '@/components/layout/ClientLayout';
import { toast } from 'sonner';
import { useConversationStore } from '@/stores/conversationStore';
import { useConversationSave } from '@/hooks/useConversationSave';

export default function GraphRAGPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [leftDrawerOpen, setLeftDrawerOpen] = useState(false);
  const [rightDrawerOpen, setRightDrawerOpen] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null); // Claude Agent SDK session
  const abortControllerRef = useRef<AbortController | null>(null);
  const messageTimestampsRef = useRef<number[]>([]);
  
  // Conversation store for persistence
  const { 
    currentConversation, 
    loadConversation, 
    createConversation
  } = useConversationStore();

  // Conversation save hook with rate limiting and deduplication
  const { saveMessages } = useConversationSave();

  // Real-time crawl progress polling with proper cleanup
  useEffect(() => {
    const activeCrawls = messages.filter(m => m.crawl?.status === 'active');
    if (activeCrawls.length === 0) return;

    const intervals = new Map<string, NodeJS.Timeout>();
    let isMounted = true;

    activeCrawls.forEach((message) => {
      if (!message.crawl) return;

      const { jobId } = message.crawl;

      // Skip if already polling this job
      if (intervals.has(jobId)) return;

      const pollStatus = async () => {
        try {
          const response = await fetch(`/api/crawl/status/${jobId}`);
          if (!response.ok) return;

          const statusData = await response.json();
          const status = statusData.status;
          const isComplete = status === 'completed' || status === 'failed';

          // Extract recent pages
          const recentPages = statusData.data && statusData.data.length > 0
            ? statusData.data.slice(-5).map((p: Record<string, unknown>) => ({
                url: (p.metadata as Record<string, unknown>)?.sourceURL || 'Unknown',
                status: 'completed'
              }))
            : [];

          // Only update if component is still mounted
          if (isMounted) {
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
          }

          // Stop polling if complete
          if (isComplete && intervals.has(jobId)) {
            clearInterval(intervals.get(jobId)!);
            intervals.delete(jobId);
          }

        } catch (error) {
          if (isMounted) {
            console.error('Failed to poll crawl status:', error);
          }
        }
      };

      // Poll immediately, then every 3 seconds
      pollStatus();
      const interval = setInterval(pollStatus, 3000);
      intervals.set(jobId, interval);
    });

    // Cleanup function
    return () => {
      isMounted = false;
      intervals.forEach(interval => clearInterval(interval));
      intervals.clear();
    };
  }, [messages]);

  // Cleanup: abort any in-flight requests on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, []);

  // Load messages from current conversation
  useEffect(() => {
    if (currentConversation?.messages) {
      // Convert backend messages to UI message format
      const uiMessages: ChatMessage[] = currentConversation.messages.map(msg => ({
        id: msg.id,
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
        timestamp: new Date(msg.created_at).toLocaleTimeString('en-US', { 
          hour: 'numeric', 
          minute: '2-digit' 
        }),
        citations: msg.sources?.length ? msg.sources.map((s, i) => ({
          number: i + 1,
          title: s.payload?.metadata?.title || s.payload?.metadata?.sourceURL || 'Source'
        })) : undefined
      }));
      setMessages(uiMessages);
    }
  }, [currentConversation]);

  const handleCommand = async (command: string, args: string) => {
    const userMessage: ChatMessage = {
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
          const responseMessage: ChatMessage = {
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
          if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
            throw new Error(`Map failed: ${errorData.error || response.statusText}`);
          }
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
          const fullResults = data.results.map((r: Record<string, string>, i: number) => 
            `### ${i + 1}. ${r.title}\n**URL**: ${r.url}\n\n${r.content}\n`
          ).join('\n---\n\n');
          result = data.results.map((r: Record<string, string>, i: number) => 
            `### ${i + 1}. ${r.title}\n**URL**: ${r.url}\n\n${r.content.substring(0, 300)}...\n`
          ).join('\n---\n\n');
          artifactTitle = 'Search Results';
          
          // Store full search results in metadata for assistant context
          const responseMessage: ChatMessage = {
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
          const responseMessage: ChatMessage = {
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
            ? statusData.data.slice(-5).map((p: Record<string, unknown>) => ({
                url: (p.metadata as Record<string, unknown>)?.sourceURL || 'Unknown',
                status: 'completed'
              }))
            : [];
          
          // Crawl status - use CrawlProgress component (no artifact)
          const responseMessage: ChatMessage = {
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
      
    } catch (error: unknown) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `❌ ${errorMsg}`,
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

  // Helper: Safely trigger save outside render cycle
  // This queues the save to happen asynchronously without blocking
  const queueSave = (userMessage: string, assistantMessage: string) => {
    // Use queueMicrotask to ensure this runs after render completes
    queueMicrotask(() => {
      saveMessages({
        userMessage,
        assistantMessage,
        conversationId: currentConversation?.id
      }).catch(error => {
        console.error('Background save failed:', error);
      });
    });
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
      toast.error('Rate limit exceeded', {
        description: 'You can only send 5 messages per minute. Please wait.',
        duration: 4000,
      });
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
    const userMessage: ChatMessage = {
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
        const scrapeMessage: ChatMessage = {
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
      } catch (scrapeError: unknown) {
        console.error('Scrape error:', scrapeError);
        // Show error message
        const scrapeErrorMsg = scrapeError instanceof Error ? scrapeError.message : 'Unknown error';
        const errorMessage: ChatMessage = {
          id: (Date.now() + 0.5).toString(),
          role: 'assistant',
          content: [`❌ Failed to scrape URL: ${scrapeErrorMsg}`],
          timestamp: new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
        };
        setMessages(prev => [...prev, errorMessage]);
        setIsLoading(false);
        return;
      }
    }

    // Create assistant message placeholder for streaming
    const assistantId = (Date.now() + 1).toString();
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: [], // Start with empty ContentSegment array
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
      const contentSegments: ContentSegment[] = []; // Build inline content
      let currentTextSegment = ''; // Accumulate current text
      const toolsInUse = new Map<string, { name: string; input: string; index: number }>(); // Track tool calls by ID
      let buffer = ''; // Buffer for incomplete lines

      if (!reader) {
        throw new Error('No response body');
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk; // Add to buffer
        const lines = buffer.split('\n');
        
        // Keep the last incomplete line in buffer
        buffer = lines.pop() || '';

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
            // Skip empty or malformed data
            if (!data || data.trim() === '') continue;
            
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

              // Tool use started - insert inline
              if (event?.type === 'content_block_start' && event.content_block?.type === 'tool_use') {
                const toolId = event.content_block.id;
                const toolName = event.content_block.name;
                const segmentIndex = contentSegments.length;
                toolsInUse.set(toolId, { name: toolName, input: '', index: segmentIndex });

                // Flush any accumulated text before tool
                if (currentTextSegment) {
                  contentSegments.push({ type: 'text', text: currentTextSegment });
                  currentTextSegment = '';
                }

                // Add tool call inline
                contentSegments.push({
                  type: 'tool',
                  command: toolName,
                  args: '',
                  status: 'running'
                });

                // Update UI
                setMessages(prev =>
                  prev.map(m => m.id === assistantId
                    ? { ...m, content: [...contentSegments] }
                    : m
                  )
                );
              }

              // Tool input streaming (parameters)
              if (event?.type === 'content_block_delta' && event.delta?.type === 'input_json_delta') {
                const contentBlockIndex = event.index;
                const partialJson = event.delta.partial_json;

                // Find tool by content block index
                for (const [toolId, tool] of toolsInUse.entries()) {
                  // Match by checking if this is the right content block
                  const toolIds = Array.from(toolsInUse.keys());
                  if (toolIds.indexOf(toolId) === contentBlockIndex) {
                    tool.input += partialJson;

                    // Try to parse and update tool segment
                    try {
                      const parsedArgs = JSON.parse(tool.input);
                      const argsStr = Object.entries(parsedArgs)
                        .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
                        .join(', ');

                      // Update the tool segment inline
                      if (contentSegments[tool.index]?.type === 'tool') {
                        contentSegments[tool.index] = {
                          type: 'tool',
                          command: tool.name,
                          args: argsStr,
                          status: 'running'
                        };

                        setMessages(prev =>
                          prev.map(m => m.id === assistantId
                            ? { ...m, content: [...contentSegments] }
                            : m
                          )
                        );
                      }
                    } catch {
                      // JSON not complete yet, keep accumulating
                    }
                    break;
                  }
                }
              }

              // Tool completed
              if (event?.type === 'content_block_stop') {
                const contentBlockIndex = event.index;

                // Mark tool as complete
                for (const [toolId, tool] of toolsInUse.entries()) {
                  const toolIds = Array.from(toolsInUse.keys());
                  if (toolIds.indexOf(toolId) === contentBlockIndex) {
                    if (contentSegments[tool.index]?.type === 'tool') {
                      contentSegments[tool.index] = {
                        ...(contentSegments[tool.index] as { type: 'tool'; command: string; args?: string }),
                        status: 'complete'
                      };

                      setMessages(prev =>
                        prev.map(m => m.id === assistantId
                          ? { ...m, content: [...contentSegments] }
                          : m
                        )
                      );
                    }
                    break;
                  }
                }
              }

              // Streaming text response - accumulate and add inline
              if (event?.type === 'content_block_delta' && event.delta?.type === 'text_delta') {
                currentTextSegment += event.delta.text;

                // Update the last text segment or add new one
                const lastSegment = contentSegments[contentSegments.length - 1];
                if (lastSegment?.type === 'text') {
                  lastSegment.text = currentTextSegment;
                } else {
                  contentSegments.push({ type: 'text', text: currentTextSegment });
                }

                setMessages(prev =>
                  prev.map(m => m.id === assistantId
                    ? { ...m, content: [...contentSegments] }
                    : m
                  )
                );
              }
            } else if (parsed.type === 'result') {
              // Final result - flush any remaining text
              if (currentTextSegment && !contentSegments.some(s => s.type === 'text' && s.text === currentTextSegment)) {
                contentSegments.push({ type: 'text', text: currentTextSegment });
              }

              setMessages(prev =>
                prev.map(m => m.id === assistantId
                  ? { ...m, content: contentSegments.length > 0 ? contentSegments : [{ type: 'text', text: parsed.result || '' }], isStreaming: false }
                  : m
                )
              );
              setIsLoading(false);
            } else if (parsed.type === 'error') {
              throw new Error(parsed.error || 'Unknown error');
            }
          } catch (parseError) {
            // Silently skip incomplete JSON chunks - they'll be completed in next iteration
            // Only log if it's not a JSON parsing error
            if (parseError instanceof Error && !parseError.message.includes('JSON')) {
              console.error('Error parsing SSE data:', parseError);
            }
          }
        }
      }
    } catch (error: unknown) {
      console.error('Chat error:', error);
      setIsLoading(false);

      // Update assistant message with error
      const errorMessage = error instanceof Error ? error.message : 'Failed to get response';
      setMessages(prev =>
        prev.map(m => m.id === assistantId
          ? {
              ...m,
              content: [{ type: 'text' as const, text: `Error: ${errorMessage}` }],
              isStreaming: false
            }
          : m
        )
      );
    } finally {
      abortControllerRef.current = null;
      
      // Queue save operation (runs after render with rate limiting and deduplication)
      setTimeout(() => {
        setMessages(currentMessages => {
          const assistantMsg = currentMessages.find(m => m.id === assistantId);
          if (assistantMsg) {
            const assistantContent = assistantMsg.content;
            const assistantText = Array.isArray(assistantContent)
              ? assistantContent.map(seg => 
                  typeof seg === 'string' ? seg : seg.type === 'text' ? seg.text : ''
                ).join('')
              : String(assistantContent);
            
            // Queue save with all safety guardrails
            if (assistantText.trim()) {
              queueSave(content, assistantText);
            }
          }
          return currentMessages; // Don't modify state, just read it
        });
      }, 100);
    }
  };

  return (
    <ClientLayout
      messages={messages}
      isLoading={isLoading}
      onSendMessage={handleSendMessage}
      onCommand={handleCommand}
      onCancelCrawl={handleCancelCrawl}
      leftDrawerOpen={leftDrawerOpen}
      rightDrawerOpen={rightDrawerOpen}
      onLeftDrawerChange={setLeftDrawerOpen}
      onRightDrawerChange={setRightDrawerOpen}
    />
  );
}
