/**
 * Integration Tests - Conversation Save Flow
 * 
 * End-to-end tests for the complete save flow with all protection layers
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useConversationSave } from '@/hooks/useConversationSave';
import { withRateLimit, getRateLimiter } from '@/lib/apiMiddleware';
import { NextRequest, NextResponse } from 'next/server';
import * as conversationStore from '@/stores/conversationStore';

// Mock the conversation store
vi.mock('@/stores/conversationStore', () => ({
  useConversationStore: vi.fn(),
}));

describe('Integration: Conversation Save Flow', () => {
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
  });

  it('should complete full save flow with all protection layers', async () => {
    // Mock API endpoint with rate limiting
    const mockApiHandler = vi.fn().mockResolvedValue(
      NextResponse.json({ success: true })
    );

    const rateLimitedApi = withRateLimit(
      getRateLimiter('message'),
      mockApiHandler
    );

    // Mock fetch to use our rate-limited handler
    global.fetch = vi.fn().mockImplementation(async (url: string) => {
      const request = new NextRequest(url as string);
      return rateLimitedApi(request);
    });

    const { result } = renderHook(() => useConversationSave());

    // Save should succeed with all layers active
    const response = await result.current.saveMessages({
      userMessage: 'Hello',
      assistantMessage: 'Hi there!',
    });

    expect(response.success).toBe(true);
    expect(mockApiHandler).toHaveBeenCalledTimes(2); // user + assistant
  });

  it('should handle client-side rate limit before reaching server', async () => {
    const mockApiHandler = vi.fn().mockResolvedValue(
      NextResponse.json({ success: true })
    );

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    });

    const { result } = renderHook(() => useConversationSave());

    // Fill client-side rate limit (3 requests / 10s)
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

    // 4th should be blocked client-side
    const response = await result.current.saveMessages({
      userMessage: 'Message 4',
      assistantMessage: 'Response 4',
    });

    expect(response.success).toBe(false);
    expect(response.reason).toBe('rate_limited');
    
    // API shouldn't be called for 4th request
    expect(global.fetch).toHaveBeenCalledTimes(6); // 3 saves × 2 messages
  });

  it('should handle server-side rate limit', async () => {
    const mockApiHandler = vi.fn().mockResolvedValue(
      NextResponse.json({ success: true })
    );

    const rateLimitedApi = withRateLimit(
      getRateLimiter('message'),
      mockApiHandler
    );

    // Create mock request factory
    const createRequest = (ip: string) => {
      const headers = new Headers({
        'x-forwarded-for': ip,
        'user-agent': 'test-agent',
      });
      return new NextRequest('http://localhost:3000/api/test', { headers });
    };

    // Fill server-side rate limit (5 requests / 10s)
    const requests = Array(6).fill(null).map(() => 
      rateLimitedApi(createRequest('192.168.1.1'))
    );

    const responses = await Promise.all(requests);

    // First 5 should succeed
    expect(responses.slice(0, 5).every(r => r.status === 200)).toBe(true);
    
    // 6th should be rate limited
    expect(responses[5].status).toBe(429);
  });

  it('should handle deduplication across multiple attempts', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    });

    const { result } = renderHook(() => useConversationSave());

    // Make same save 3 times
    const response1 = await result.current.saveMessages({
      userMessage: 'Duplicate',
      assistantMessage: 'Content',
    });

    const response2 = await result.current.saveMessages({
      userMessage: 'Duplicate',
      assistantMessage: 'Content',
    });

    const response3 = await result.current.saveMessages({
      userMessage: 'Duplicate',
      assistantMessage: 'Content',
    });

    // First should succeed
    expect(response1.success).toBe(true);
    
    // Others should be caught by deduplication
    expect(response2.success).toBe(false);
    expect(response2.reason).toBe('duplicate');
    expect(response3.success).toBe(false);
    expect(response3.reason).toBe('duplicate');
  });

  it('should handle circuit breaker opening and recovery', async () => {
    let failureCount = 0;
    
    // Fail first 5 requests, then succeed
    global.fetch = vi.fn().mockImplementation(async () => {
      if (failureCount < 5) {
        failureCount++;
        throw new Error('Network error');
      }
      return {
        ok: true,
        json: async () => ({ success: true }),
      };
    });

    const { result } = renderHook(() => useConversationSave());

    // Trigger 5 failures to open circuit
    for (let i = 0; i < 5; i++) {
      await result.current.saveMessages({
        userMessage: `Message ${i}`,
        assistantMessage: `Response ${i}`,
      });
    }

    // Circuit should be open
    const response = await result.current.saveMessages({
      userMessage: 'After failures',
      assistantMessage: 'Should be blocked',
    });

    expect(response.success).toBe(false);
    expect(response.reason).toBe('circuit_open');

    // Reset circuit
    result.current.resetLimits();

    // Should work again
    const afterReset = await result.current.saveMessages({
      userMessage: 'After reset',
      assistantMessage: 'Should work',
    });

    expect(afterReset.success).toBe(true);
  });

  it('should create conversation when none exists', async () => {
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

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    });

    const { result } = renderHook(() => useConversationSave());

    const response = await result.current.saveMessages({
      userMessage: 'First message',
      assistantMessage: 'First response',
    });

    expect(response.success).toBe(true);
    expect(mockCreateConversation).toHaveBeenCalledWith('First message');
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/conversations/new-conv-id/messages',
      expect.any(Object)
    );
  });

  it('should handle partial failures gracefully', async () => {
    // User message succeeds, assistant fails
    let callCount = 0;
    global.fetch = vi.fn().mockImplementation(async () => {
      callCount++;
      if (callCount === 2) {
        return { ok: false, status: 500 };
      }
      return {
        ok: true,
        json: async () => ({ success: true }),
      };
    });

    const { result } = renderHook(() => useConversationSave());

    const response = await result.current.saveMessages({
      userMessage: 'Hello',
      assistantMessage: 'Hi there!',
    });

    expect(response.success).toBe(false);
    expect(response.reason).toBe('error');
  });

  it('should handle network timeout', async () => {
    global.fetch = vi.fn().mockImplementation(
      () => new Promise((_, reject) => 
        setTimeout(() => reject(new Error('timeout')), 100)
      )
    );

    const { result } = renderHook(() => useConversationSave());

    const response = await result.current.saveMessages({
      userMessage: 'Hello',
      assistantMessage: 'Hi there!',
    });

    expect(response.success).toBe(false);
    expect(response.reason).toBe('error');
  });

  it('should reload conversation after successful save', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    });

    const { result } = renderHook(() => useConversationSave());

    await result.current.saveMessages({
      userMessage: 'Hello',
      assistantMessage: 'Hi there!',
    });

    expect(mockLoadConversation).toHaveBeenCalledWith('conv-123');
  });

  it('should handle rapid sequential saves with all protections', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    });

    const { result } = renderHook(() => useConversationSave());

    // Rapid fire 10 saves
    const promises = Array(10).fill(null).map((_, i) => 
      result.current.saveMessages({
        userMessage: `Message ${i}`,
        assistantMessage: `Response ${i}`,
      })
    );

    const results = await Promise.all(promises);

    // First 3 should succeed (client rate limit)
    const succeeded = results.filter(r => r.success).length;
    const rateLimited = results.filter(
      r => !r.success && r.reason === 'rate_limited'
    ).length;
    const inProgress = results.filter(
      r => !r.success && r.reason === 'in_progress'
    ).length;

    expect(succeeded).toBeLessThanOrEqual(3);
    expect(rateLimited + inProgress).toBeGreaterThan(0);
  });
});
