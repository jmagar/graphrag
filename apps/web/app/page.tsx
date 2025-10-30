"use client";

import { useState, useRef } from 'react';
import { LeftSidebar } from '@/components/layout/LeftSidebar';
import { RightSidebar } from '@/components/layout/RightSidebar';
import { ChatHeader } from '@/components/chat/ChatHeader';
import { AIMessage } from '@/components/chat/AIMessage';
import { UserMessage } from '@/components/chat/UserMessage';
import { ChatInput } from '@/components/input/ChatInput';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string | string[];
  citations?: Array<{ number: number; title: string }>;
  timestamp: string;
  isStreaming?: boolean;
}

export default function GraphRAGPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const messageTimestampsRef = useRef<number[]>([]);

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

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    // Create assistant message placeholder for streaming
    const assistantId = (Date.now() + 1).toString();
    const assistantMessage: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }),
      isStreaming: true
    };
    setMessages(prev => [...prev, assistantMessage]);

    try {
      // Create abort controller for this request
      abortControllerRef.current = new AbortController();

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: content,
          history: messages.map(m => ({
            role: m.role,
            content: Array.isArray(m.content) ? m.content.join('\n') : m.content
          }))
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedContent = '';

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

            // Handle different message types from Claude Agent SDK
            // ONLY use stream_event for live updates to avoid duplicates
            if (parsed.type === 'stream_event') {
              // Streaming partial messages
              const event = parsed.event;
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
      {/* Left Sidebar */}
      <LeftSidebar />
      
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-zinc-50 dark:bg-zinc-900">
        <ChatHeader />
        
        {/* Messages */}
        <div className="flex-1 overflow-y-auto custom-scroll pb-32">
          <div className="max-w-3xl mx-auto px-6 py-12 space-y-6">
            {messages.map((message) =>
              message.role === 'assistant' ? (
                <AIMessage
                  key={message.id}
                  content={Array.isArray(message.content) ? message.content : [message.content]}
                  citations={message.citations}
                  timestamp={message.timestamp}
                />
              ) : (
                <UserMessage
                  key={message.id}
                  content={message.content as string}
                  timestamp={message.timestamp}
                />
              )
            )}
          </div>
        </div>
        
        {/* Input Area */}
        <ChatInput onSend={handleSendMessage} />
      </div>
      
      {/* Right Sidebar */}
      <RightSidebar />
    </div>
  );
}
