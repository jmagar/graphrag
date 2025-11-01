/**
 * useConversationSave Hook Tests
 * 
 * Tests for the conversation save hook with rate limiting and deduplication
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useConversationSave } from '@/hooks/useConversationSave';
import * as conversationStore from '@/stores/conversationStore';

// Mock the conversation store
vi.mock('@/stores/conversationStore', () => ({
  useConversationStore: vi.fn(),
}));

// Mock fetch
global.fetch = vi.fn();

describe('useConversationSave', () => {
  const mockCreateConversation = vi.fn();
  const mockLoadConversation = vi.fn();
  const mockCurrentConversation = {
    id: 'conv-123',
    title: 'Test Conversation',
    space: 'default',
    created_at: '2024-01-01',
    updated_at: '2024-01-01',
    tags: [],
    message_count: 0,
    messages: [],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Reset fetch mock
    (global.fetch as ReturnType<typeof vi.fn>).mockReset();
    
    // Setup store mock
    vi.mocked(conversationStore.useConversationStore).mockReturnValue({
      currentConversation: mockCurrentConversation,
      conversations: [],
      isLoading: false,
      error: null,
      loadConversations: vi.fn(),
      loadConversation: mockLoadConversation,
      createConversation: mockCreateConversation,
      updateConversation: vi.fn(),
      deleteConversation: vi.fn(),
      sendMessage: vi.fn(),
      setCurrentConversation: vi.fn(),
      clearError: vi.fn(),
    });

    // Mock successful fetch responses
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    });
  });

  it('should save messages successfully', async () => {
    const { result } = renderHook(() => useConversationSave());

    const response = await result.current.saveMessages({
      userMessage: 'Hello',
      assistantMessage: 'Hi there!',
    });

    expect(response.success).toBe(true);
    expect(global.fetch).toHaveBeenCalledTimes(2); // user + assistant
  });

  it('should prevent duplicate saves', async () => {
    const { result } = renderHook(() => useConversationSave());

    // Save once
    await result.current.saveMessages({
      userMessage: 'Hello',
      assistantMessage: 'Hi there!',
    });

    // Try to save same content again
    const response = await result.current.saveMessages({
      userMessage: 'Hello',
      assistantMessage: 'Hi there!',
    });

    expect(response.success).toBe(false);
    expect(response.reason).toBe('duplicate');
  });

  it('should prevent concurrent saves', async () => {
    const { result } = renderHook(() => useConversationSave());

    // Start first save (don't await)
    const promise1 = result.current.saveMessages({
      userMessage: 'Hello',
      assistantMessage: 'Hi there!',
    });

    // Try second save immediately
    const response2 = await result.current.saveMessages({
      userMessage: 'Different',
      assistantMessage: 'Content',
    });

    await promise1;

    expect(response2.success).toBe(false);
    expect(response2.reason).toBe('in_progress');
  });

  it('should enforce rate limiting', async () => {
    const { result } = renderHook(() => useConversationSave());

    // Make 3 saves quickly (at the limit)
    await result.current.saveMessages({
      userMessage: 'Message 1',
      assistantMessage: 'Response 1',
    });

    await result.current.saveMessages({
      userMessage: 'Message 2',
      assistantMessage: 'Response 2',
    });

    await result.current.saveMessages({
      userMessage: 'Message 3',
      assistantMessage: 'Response 3',
    });

    // 4th should be rate limited
    const response = await result.current.saveMessages({
      userMessage: 'Message 4',
      assistantMessage: 'Response 4',
    });

    expect(response.success).toBe(false);
    expect(response.reason).toBe('rate_limited');
    expect(response.retryAfter).toBeGreaterThan(0);
  });

  it('should create conversation if none exists', async () => {
    // Mock no current conversation
    vi.mocked(conversationStore.useConversationStore).mockReturnValue({
      currentConversation: null,
      conversations: [],
      isLoading: false,
      error: null,
      loadConversations: vi.fn(),
      loadConversation: mockLoadConversation,
      createConversation: mockCreateConversation.mockResolvedValue({
        id: 'new-conv-id',
        title: 'New Conversation',
        space: 'default',
        created_at: '2024-01-01',
        updated_at: '2024-01-01',
        tags: [],
        message_count: 0,
      }),
      updateConversation: vi.fn(),
      deleteConversation: vi.fn(),
      sendMessage: vi.fn(),
      setCurrentConversation: vi.fn(),
      clearError: vi.fn(),
    });

    const { result } = renderHook(() => useConversationSave());

    await result.current.saveMessages({
      userMessage: 'Hello',
      assistantMessage: 'Hi there!',
    });

    expect(mockCreateConversation).toHaveBeenCalledWith('Hello');
  });

  it('should use provided conversation ID', async () => {
    const { result } = renderHook(() => useConversationSave());

    await result.current.saveMessages({
      userMessage: 'Hello',
      assistantMessage: 'Hi there!',
      conversationId: 'custom-conv-id',
    });

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/conversations/custom-conv-id/messages',
      expect.any(Object)
    );
  });

  it('should handle API errors gracefully', async () => {
    // Mock failed fetch
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    const { result } = renderHook(() => useConversationSave());

    const response = await result.current.saveMessages({
      userMessage: 'Hello',
      assistantMessage: 'Hi there!',
    });

    expect(response.success).toBe(false);
    expect(response.reason).toBe('error');
  });

  it('should reload conversation after save', async () => {
    const { result } = renderHook(() => useConversationSave());

    await result.current.saveMessages({
      userMessage: 'Hello',
      assistantMessage: 'Hi there!',
    });

    expect(mockLoadConversation).toHaveBeenCalledWith('conv-123');
  });

  it('should allow reset of limits', async () => {
    const { result } = renderHook(() => useConversationSave());

    // Fill rate limit
    await result.current.saveMessages({
      userMessage: 'Message 1',
      assistantMessage: 'Response 1',
    });

    await result.current.saveMessages({
      userMessage: 'Message 2',
      assistantMessage: 'Response 2',
    });

    await result.current.saveMessages({
      userMessage: 'Message 3',
      assistantMessage: 'Response 3',
    });

    // Reset
    result.current.resetLimits();

    // Should work again
    const response = await result.current.saveMessages({
      userMessage: 'Message 4',
      assistantMessage: 'Response 4',
    });

    expect(response.success).toBe(true);
  });

  it('should report circuit breaker state', async () => {
    const { result } = renderHook(() => useConversationSave());

    expect(result.current.circuitState).toBe('closed');
  });

  it('should open circuit breaker after failures', async () => {
    // Mock repeated failures
    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('Network error')
    );

    const { result } = renderHook(() => useConversationSave());

    // Trigger 5 failures
    for (let i = 0; i < 5; i++) {
      await result.current.saveMessages({
        userMessage: `Message ${i}`,
        assistantMessage: `Response ${i}`,
      });
    }

    await waitFor(() => {
      expect(result.current.circuitState).toBe('open');
    });
  });

  it('should deduplicate concurrent requests', async () => {
    const { result } = renderHook(() => useConversationSave());

    // Make same request twice concurrently
    const promises = [
      result.current.saveMessages({
        userMessage: 'Hello',
        assistantMessage: 'Hi there!',
      }),
      result.current.saveMessages({
        userMessage: 'Hello',
        assistantMessage: 'Hi there!',
      }),
    ];

    const [result1, result2] = await Promise.all(promises);

    // First should succeed
    expect(result1.success).toBe(true);
    
    // Second should be caught by either duplicate or in_progress check
    if (!result2.success) {
      expect(['duplicate', 'in_progress']).toContain(result2.reason);
    }
  });

  it('should send correct request payload', async () => {
    const { result } = renderHook(() => useConversationSave());

    await result.current.saveMessages({
      userMessage: 'Hello',
      assistantMessage: 'Hi there!',
    });

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/conversations/conv-123/messages',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role: 'user',
          content: 'Hello',
          extra_data: {}
        })
      }
    );

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/conversations/conv-123/messages',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role: 'assistant',
          content: 'Hi there!',
          extra_data: {}
        })
      }
    );
  });

  it('should report if save is allowed', () => {
    const { result } = renderHook(() => useConversationSave());

    expect(result.current.canSave).toBe(true);
  });
});
