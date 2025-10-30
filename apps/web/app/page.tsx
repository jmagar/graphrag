"use client";

import { useState } from 'react';
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
}

export default function GraphRAGPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: [
        'Based on your sources, GraphRAG combines graph databases with retrieval-augmented generation to create powerful knowledge systems.',
        'The system uses <strong class="font-semibold text-blue-600 dark:text-blue-400">Qdrant</strong> for vector storage with TEI embeddings in a 768-dimensional space.'
      ],
      citations: [{ number: 1, title: 'Getting Started' }],
      timestamp: '2:34 PM'
    },
    {
      id: '2',
      role: 'user',
      content: 'How do I configure the embedding dimensions?',
      timestamp: '2:35 PM'
    }
  ]);

  const handleSendMessage = (content: string) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
    };
    setMessages([...messages, newMessage]);
    
    // Simulate AI response after a short delay
    setTimeout(() => {
      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: ['I can help you with that! Let me search through your documentation...'],
        timestamp: new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
      };
      setMessages(prev => [...prev, aiResponse]);
    }, 1000);
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
