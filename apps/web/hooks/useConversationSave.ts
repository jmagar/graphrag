/**
 * Hook for saving conversations with rate limiting and deduplication
 */

import { useCallback, useRef } from 'react';
import { ClientRateLimiter, CircuitBreaker, RATE_LIMIT_CONFIG } from '@/lib/rateLimit';
import { useConversationStore } from '@/stores/conversationStore';

// Create singleton instances
const rateLimiter = new ClientRateLimiter();
const circuitBreaker = new CircuitBreaker(5, 60000); // 5 failures, 1 min reset

interface SaveMessageOptions {
  userMessage: string;
  assistantMessage: string;
  conversationId?: string;
}

export function useConversationSave() {
  const { currentConversation, createConversation, loadConversation } = useConversationStore();
  const saveInProgressRef = useRef(false);
  const lastSaveHashRef = useRef<string>('');

  /**
   * Generate hash for deduplication
   */
  const generateHash = useCallback((user: string, assistant: string): string => {
    return `${user.substring(0, 50)}-${assistant.substring(0, 50)}`;
  }, []);

  /**
   * Save messages to backend with all safety guards
   */
  const saveMessages = useCallback(async (options: SaveMessageOptions) => {
    const { userMessage, assistantMessage, conversationId } = options;

    // Generate hash for deduplication
    const hash = generateHash(userMessage, assistantMessage);
    
    // Skip if duplicate
    if (hash === lastSaveHashRef.current) {
      console.debug('Skipping duplicate save request');
      return { success: false, reason: 'duplicate' };
    }

    // Skip if save already in progress
    if (saveInProgressRef.current) {
      console.debug('Save already in progress, skipping');
      return { success: false, reason: 'in_progress' };
    }

    // Check rate limit
    const saveKey = 'conversation-save';
    if (!rateLimiter.isAllowed(
      saveKey,
      RATE_LIMIT_CONFIG.CLIENT_CONVERSATION_SAVE.maxRequests,
      RATE_LIMIT_CONFIG.CLIENT_CONVERSATION_SAVE.windowMs
    )) {
      console.warn('Rate limit exceeded for conversation save');
      return { 
        success: false, 
        reason: 'rate_limited'
      };
    }

    // Check circuit breaker
    if (circuitBreaker.getState() === 'open') {
      console.error('Circuit breaker is open. Too many failures.');
      return { success: false, reason: 'circuit_open' };
    }

    try {
      saveInProgressRef.current = true;
      lastSaveHashRef.current = hash;

      // Execute with circuit breaker protection
      await circuitBreaker.execute(async () => {
        let targetConversationId = conversationId || currentConversation?.id;

        // Create conversation if needed
        if (!targetConversationId) {
          const newConv = await createConversation(
            userMessage.slice(0, 50) + (userMessage.length > 50 ? '...' : '')
          );
          targetConversationId = newConv.id;
        }

        // Use deduplication for parallel requests
        const saveKey = `save-${targetConversationId}-${hash}`;
        
        await rateLimiter.deduplicate(saveKey, async () => {
          // Save user message
          const userResponse = await fetch(
            `/api/conversations/${targetConversationId}/messages`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                role: 'user',
                content: userMessage,
                extra_data: {}
              })
            }
          );

          if (!userResponse.ok) {
            throw new Error(`Failed to save user message: ${userResponse.status}`);
          }

          // Save assistant message
          const assistantResponse = await fetch(
            `/api/conversations/${targetConversationId}/messages`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                role: 'assistant',
                content: assistantMessage,
                extra_data: {}
              })
            }
          );

          if (!assistantResponse.ok) {
            throw new Error(`Failed to save assistant message: ${assistantResponse.status}`);
          }

          // Reload conversation
          if (targetConversationId) {
            await loadConversation(targetConversationId);
          }
        });
      });

      return { success: true };
    } catch (error) {
      console.error('Failed to save conversation:', error);
      return { 
        success: false, 
        reason: 'error',
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    } finally {
      saveInProgressRef.current = false;
    }
  }, [currentConversation, createConversation, loadConversation, generateHash]);

  /**
   * Reset rate limiter (useful for testing or manual reset)
   */
  const resetLimits = useCallback(() => {
    rateLimiter.reset();
    circuitBreaker.reset();
    lastSaveHashRef.current = '';
  }, []);

  return {
    saveMessages,
    resetLimits,
    canSave: rateLimiter.isAllowed(
      'conversation-save',
      RATE_LIMIT_CONFIG.CLIENT_CONVERSATION_SAVE.maxRequests,
      RATE_LIMIT_CONFIG.CLIENT_CONVERSATION_SAVE.windowMs
    ),
    circuitState: circuitBreaker.getState()
  };
}
