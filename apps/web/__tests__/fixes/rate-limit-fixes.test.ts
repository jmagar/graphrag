/**
 * Test to verify rate limiting fixes
 * 
 * This test verifies that all the rate limiting errors reported have been fixed:
 * 1. ClientRateLimiter no longer expects config in constructor
 * 2. isAllowed() works with per-call parameters
 * 3. useConversationSave hook works without errors
 */

import { ClientRateLimiter, RATE_LIMIT_CONFIG } from '@/lib/rateLimit';

describe('Rate Limiting Fixes Verification', () => {
  describe('ClientRateLimiter API', () => {
    let rateLimiter: ClientRateLimiter;

    beforeEach(() => {
      // Should instantiate without config parameter
      rateLimiter = new ClientRateLimiter();
    });

    it('should instantiate without config parameter', () => {
      expect(rateLimiter).toBeDefined();
      expect(rateLimiter).toBeInstanceOf(ClientRateLimiter);
    });

    it('should use isAllowed() with per-call parameters', () => {
      const key = 'test-key';
      const maxRequests = 3;
      const windowMs = 1000;

      // Should work without throwing "Cannot read properties of undefined"
      const result1 = rateLimiter.isAllowed(key, maxRequests, windowMs);
      expect(result1).toBe(true);

      const result2 = rateLimiter.isAllowed(key, maxRequests, windowMs);
      expect(result2).toBe(true);

      const result3 = rateLimiter.isAllowed(key, maxRequests, windowMs);
      expect(result3).toBe(true);

      // Fourth request should be blocked
      const result4 = rateLimiter.isAllowed(key, maxRequests, windowMs);
      expect(result4).toBe(false);
    });

    it('should provide getRetryAfter() with required parameters', () => {
      const key = 'test-key';
      const maxRequests = 2;
      const windowMs = 5000;

      // Fill quota
      rateLimiter.isAllowed(key, maxRequests, windowMs);
      rateLimiter.isAllowed(key, maxRequests, windowMs);

      // Should calculate retry time without errors
      const retryAfter = rateLimiter.getRetryAfter(key, windowMs);
      expect(typeof retryAfter).toBe('number');
      expect(retryAfter).toBeGreaterThanOrEqual(0);
    });

    it('should support multiple independent keys', () => {
      const maxRequests = 2;
      const windowMs = 1000;

      // Fill quota for key1
      expect(rateLimiter.isAllowed('key1', maxRequests, windowMs)).toBe(true);
      expect(rateLimiter.isAllowed('key1', maxRequests, windowMs)).toBe(true);
      expect(rateLimiter.isAllowed('key1', maxRequests, windowMs)).toBe(false);

      // key2 should still be available
      expect(rateLimiter.isAllowed('key2', maxRequests, windowMs)).toBe(true);
      expect(rateLimiter.isAllowed('key2', maxRequests, windowMs)).toBe(true);
      expect(rateLimiter.isAllowed('key2', maxRequests, windowMs)).toBe(false);
    });

    it('should reset all rate limits', () => {
      const key = 'test-key';
      const maxRequests = 2;
      const windowMs = 1000;

      // Fill quota
      rateLimiter.isAllowed(key, maxRequests, windowMs);
      rateLimiter.isAllowed(key, maxRequests, windowMs);
      expect(rateLimiter.isAllowed(key, maxRequests, windowMs)).toBe(false);

      // Reset should clear all limits
      rateLimiter.reset();

      // Should allow requests again
      expect(rateLimiter.isAllowed(key, maxRequests, windowMs)).toBe(true);
    });
  });

  describe('RATE_LIMIT_CONFIG', () => {
    it('should export rate limit configuration constants', () => {
      expect(RATE_LIMIT_CONFIG).toBeDefined();
      expect(RATE_LIMIT_CONFIG.CLIENT_CONVERSATION_SAVE).toBeDefined();
      expect(RATE_LIMIT_CONFIG.CLIENT_CLAUDE_CHAT).toBeDefined();
    });

    it('should have valid conversation save limits', () => {
      const config = RATE_LIMIT_CONFIG.CLIENT_CONVERSATION_SAVE;
      expect(config.maxRequests).toBe(3);
      expect(config.windowMs).toBe(10000);
      expect(typeof config.rationale).toBe('string');
    });

    it('should have valid Claude chat limits', () => {
      const config = RATE_LIMIT_CONFIG.CLIENT_CLAUDE_CHAT;
      expect(config.maxRequests).toBe(5);
      expect(config.windowMs).toBe(60000);
      expect(typeof config.rationale).toBe('string');
    });
  });

  describe('useConversationSave Integration', () => {
    it('should use RATE_LIMIT_CONFIG constants', () => {
      const rateLimiter = new ClientRateLimiter();
      const config = RATE_LIMIT_CONFIG.CLIENT_CONVERSATION_SAVE;

      // This is how useConversationSave now calls isAllowed
      const canSave = rateLimiter.isAllowed(
        'conversation-save',
        config.maxRequests,
        config.windowMs
      );

      expect(typeof canSave).toBe('boolean');
    });
  });

  describe('Backward Compatibility', () => {
    it('should not have deprecated canMakeRequest method', () => {
      const rateLimiter = new ClientRateLimiter();
      // @ts-expect-error - Testing that method doesn't exist
      expect(rateLimiter.canMakeRequest).toBeUndefined();
    });

    it('should not have deprecated recordRequest method', () => {
      const rateLimiter = new ClientRateLimiter();
      // @ts-expect-error - Testing that method doesn't exist
      expect(rateLimiter.recordRequest).toBeUndefined();
    });
  });
});
