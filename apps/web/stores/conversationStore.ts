/**
 * Conversation Store - Zustand state management for conversations
 * 
 * Manages:
 * - Conversation list and current conversation
 * - Messages in current conversation
 * - Loading states and errors
 * - CRUD operations via backend API
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ============================================================================
// Types
// ============================================================================

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  extra_data: Record<string, unknown>;
  sources: Array<{
    id: string;
    score: number;
    payload: {
      content: string;
      metadata: {
        sourceURL: string;
        title?: string;
      };
    };
  }>;
}

export interface Conversation {
  id: string;
  title: string;
  space: string;
  created_at: string;
  updated_at: string;
  tags: string[];
  message_count: number;
  last_message_preview?: string;
}

export interface ConversationDetail extends Conversation {
  messages: ConversationMessage[];
}

// ============================================================================
// Store Interface
// ============================================================================

interface ConversationState {
  // State
  conversations: Conversation[];
  currentConversation: ConversationDetail | null;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  loadConversations: () => Promise<void>;
  loadConversation: (id: string) => Promise<void>;
  createConversation: (title: string, space?: string) => Promise<Conversation>;
  updateConversation: (id: string, data: { title?: string; tags?: string[] }) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  sendMessage: (content: string, useRag?: boolean, conversationId?: string) => Promise<ConversationMessage>;
  setCurrentConversation: (conversation: ConversationDetail | null) => void;
  clearError: () => void;
}

// ============================================================================
// Store Implementation
// ============================================================================

export const useConversationStore = create<ConversationState>()(
  persist(
    (set, get) => ({
      // Initial state
      conversations: [],
      currentConversation: null,
      isLoading: false,
      error: null,
      
      // Load all conversations
      loadConversations: async () => {
        set({ isLoading: true, error: null });
        try {
          const response = await fetch('/api/conversations');
          if (!response.ok) throw new Error('Failed to load conversations');
          
          const conversations = await response.json();
          set({ conversations, isLoading: false });
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Unknown error',
            isLoading: false 
          });
        }
      },
      
      // Load a specific conversation with messages
      loadConversation: async (id: string) => {
        set({ isLoading: true, error: null });
        try {
          const response = await fetch(`/api/conversations/${id}`);
          if (!response.ok) throw new Error('Failed to load conversation');
          
          const conversation = await response.json();
          set({ currentConversation: conversation, isLoading: false });
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Unknown error',
            isLoading: false 
          });
        }
      },
      
      // Create a new conversation
      createConversation: async (title: string, space: string = 'default') => {
        set({ isLoading: true, error: null });
        try {
          const response = await fetch('/api/conversations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, space }),
          });
          
          if (!response.ok) {
            const errorData = await response.text();
            console.error('Create conversation failed:', response.status, errorData);
            throw new Error(`Failed to create conversation: ${response.status}`);
          }
          
          const newConversation = await response.json();
          
          // Add to conversations list
          set(state => ({
            conversations: [newConversation, ...state.conversations],
            isLoading: false,
          }));
          
          return newConversation;
        } catch (error) {
          const errorMsg = error instanceof Error ? error.message : 'Unknown error';
          console.error('createConversation error:', errorMsg);
          set({ 
            error: errorMsg,
            isLoading: false 
          });
          throw error;
        }
      },
      
      // Update conversation
      updateConversation: async (id: string, data: { title?: string; tags?: string[] }) => {
        set({ isLoading: true, error: null });
        try {
          const response = await fetch(`/api/conversations/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
          });
          
          if (!response.ok) throw new Error('Failed to update conversation');
          
          const updated = await response.json();
          
          // Update in list and current
          set(state => ({
            conversations: state.conversations.map(c => 
              c.id === id ? updated : c
            ),
            currentConversation: state.currentConversation?.id === id 
              ? { ...state.currentConversation, ...updated }
              : state.currentConversation,
            isLoading: false,
          }));
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Unknown error',
            isLoading: false 
          });
          throw error;
        }
      },
      
      // Delete conversation
      deleteConversation: async (id: string) => {
        set({ isLoading: true, error: null });
        try {
          const response = await fetch(`/api/conversations/${id}`, {
            method: 'DELETE',
          });
          
          if (!response.ok) throw new Error('Failed to delete conversation');
          
          // Remove from list and clear if current
          set(state => ({
            conversations: state.conversations.filter(c => c.id !== id),
            currentConversation: state.currentConversation?.id === id 
              ? null 
              : state.currentConversation,
            isLoading: false,
          }));
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Unknown error',
            isLoading: false 
          });
          throw error;
        }
      },
      
      // Send a message (uses chat endpoint which handles SSE streaming)
      sendMessage: async (content: string, useRag: boolean = true, conversationId?: string) => {
        set({ isLoading: true, error: null });
        
        let lastMessage: ConversationMessage | null = null;
        let finalConversationId = conversationId;
        
        try {
          const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              message: content,
              use_rag: useRag,
              conversation_id: conversationId,
            }),
          });
          
          if (!response.ok) throw new Error(`Chat request failed: ${response.statusText}`);
          
          // Get the reader for SSE stream
          const reader = response.body?.getReader();
          if (!reader) throw new Error('Response body is not readable');
          
          const decoder = new TextDecoder();
          let buffer = '';
          
          try {
            while (true) {
              const { done, value } = await reader.read();
              
              if (done) break;
              
              // Decode the chunk and add to buffer
              buffer += decoder.decode(value, { stream: true });
              
              // Process complete lines
              const lines = buffer.split('\n');
              buffer = lines.pop() || ''; // Keep incomplete line in buffer
              
              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  const dataStr = line.slice(6); // Remove 'data: ' prefix
                  
                  // Check for done sentinel
                  if (dataStr === '[DONE]') {
                    continue;
                  }
                  
                  try {
                    const eventData = JSON.parse(dataStr);
                    
                    // Update state with streamed message
                    set(state => {
                      if (!state.currentConversation) return state;
                      
                      // Guard: verify conversation ID matches to prevent cross-conversation message pollution
                      if (eventData.conversation_id && state.currentConversation.id !== eventData.conversation_id) {
                        console.warn('Conversation ID mismatch in stream event - skipping update');
                        return state;
                      }
                      
                      const updatedMessages = [...state.currentConversation.messages];
                      
                      // If this is the first event and includes conversation_id, extract it
                      if (eventData.conversation_id && !finalConversationId) {
                        finalConversationId = eventData.conversation_id;
                      }
                      
                      // If this is the assistant message, update or append it
                      if (eventData.message && eventData.type === 'message') {
                        lastMessage = eventData.message;
                        
                        // Find existing message by ID and update, or append
                        const existingIndex = updatedMessages.findIndex(
                          m => m.id === eventData.message.id
                        );
                        
                        if (existingIndex >= 0) {
                          updatedMessages[existingIndex] = eventData.message;
                        } else {
                          updatedMessages.push(eventData.message);
                        }
                      }
                      
                      return {
                        currentConversation: {
                          ...state.currentConversation,
                          messages: updatedMessages,
                        },
                      };
                    });
                  } catch (parseError) {
                    console.warn('Failed to parse SSE data:', dataStr, parseError);
                  }
                }
              }
            }
          } finally {
            reader.releaseLock();
          }
          
          // Add user message if not already in conversation
          set(state => {
            if (!state.currentConversation) return state;
            
            const hasUserMessage = state.currentConversation.messages.some(
              m => m.role === 'user' && m.content === content && 
                   m.created_at === new Date().toISOString()
            );
            
            if (!hasUserMessage) {
              const userMessage: ConversationMessage = {
                id: `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                conversation_id: finalConversationId || conversationId || '',
                role: 'user',
                content,
                created_at: new Date().toISOString(),
                extra_data: {},
                sources: [],
              };
              
              return {
                currentConversation: {
                  ...state.currentConversation,
                  messages: [
                    ...state.currentConversation.messages,
                    userMessage,
                  ],
                },
                isLoading: false,
              };
            }
            
            return { isLoading: false };
          });
          
          return lastMessage || {
            id: 'error',
            conversation_id: finalConversationId || conversationId || '',
            role: 'assistant',
            content: 'No response received',
            created_at: new Date().toISOString(),
            extra_data: {},
            sources: [],
          };
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Unknown error',
            isLoading: false 
          });
          throw error;
        }
      },
      
      // Set current conversation
      setCurrentConversation: (conversation: ConversationDetail | null) => {
        set({ currentConversation: conversation });
      },
      
      // Clear error
      clearError: () => {
        set({ error: null });
      },
    }),
    {
      name: 'conversation-storage',
      // Only persist the current conversation ID
      partialize: (state) => ({ 
        currentConversationId: state.currentConversation?.id 
      }),
    }
  )
);
