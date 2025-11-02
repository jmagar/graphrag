/**
 * Rate Limiting Utilities
 * 
 * Provides client-side and server-side rate limiting to prevent API abuse
 */

interface RateLimitConfig {
  maxRequests: number;
  windowMs: number;
  keyGenerator?: (identifier: string) => string;
}

interface RateLimitEntry {
  count: number;
  resetTime: number;
}

/**
 * In-memory rate limiter (server-side)
 */
export class RateLimiter {
  private store = new Map<string, RateLimitEntry>();
  private config: Required<RateLimitConfig>;

  constructor(config: RateLimitConfig) {
    this.config = {
      ...config,
      keyGenerator: config.keyGenerator || ((id) => id)
    };

    // Cleanup expired entries every minute
    setInterval(() => this.cleanup(), 60000);
  }

  /**
   * Check if request is allowed
   */
  check(identifier: string): { allowed: boolean; retryAfter?: number } {
    const key = this.config.keyGenerator(identifier);
    const now = Date.now();
    const entry = this.store.get(key);

    // No entry or expired - allow and create new entry
    if (!entry || entry.resetTime <= now) {
      this.store.set(key, {
        count: 1,
        resetTime: now + this.config.windowMs
      });
      return { allowed: true };
    }

    // Under limit - increment and allow
    if (entry.count < this.config.maxRequests) {
      entry.count++;
      return { allowed: true };
    }

    // Over limit - deny
    const retryAfter = Math.ceil((entry.resetTime - now) / 1000);
    return { allowed: false, retryAfter };
  }

  /**
   * Reset rate limit for identifier
   */
  reset(identifier: string): void {
    const key = this.config.keyGenerator(identifier);
    this.store.delete(key);
  }

  /**
   * Cleanup expired entries
   */
  private cleanup(): void {
    const now = Date.now();
    for (const [key, entry] of this.store.entries()) {
      if (entry.resetTime <= now) {
        this.store.delete(key);
      }
    }
  }
}

/**
 * Client-side rate limiter with request deduplication
 */
export class ClientRateLimiter {
  private requests = new Map<string, number[]>();
  private pendingRequests = new Map<string, Promise<unknown>>();

  constructor() {
    // No config needed - uses per-request limits
  }

  /**
   * Check if request is allowed (key-based with custom limits)
   */
  isAllowed(key: string, maxRequests: number, windowMs: number): boolean {
    const now = Date.now();
    const cutoff = now - windowMs;

    // Get timestamps for this key
    let timestamps = this.requests.get(key) || [];

    // Remove old timestamps
    timestamps = timestamps.filter(ts => ts > cutoff);

    // Check if under limit
    if (timestamps.length < maxRequests) {
      timestamps.push(now);
      this.requests.set(key, timestamps);
      return true;
    }

    return false;
  }

  /**
   * Get time until next request is allowed for a specific key
   */
  getRetryAfter(key: string, windowMs: number): number {
    const timestamps = this.requests.get(key) || [];
    if (timestamps.length === 0) return 0;

    const oldestTimestamp = timestamps[0];
    const resetTime = oldestTimestamp + windowMs;
    const retryAfter = Math.ceil((resetTime - Date.now()) / 1000);
    return Math.max(0, retryAfter);
  }

  /**
   * Deduplicate requests with the same key
   */
  async deduplicate<T>(
    key: string,
    requestFn: () => Promise<T>
  ): Promise<T> {
    // Return existing pending request if available
    const pending = this.pendingRequests.get(key);
    if (pending) {
      return pending as Promise<T>;
    }

    // Create new request
    const promise = requestFn().finally(() => {
      this.pendingRequests.delete(key);
    });

    this.pendingRequests.set(key, promise);
    return promise;
  }

  /**
   * Reset all limits
   */
  reset(): void {
    this.requests.clear();
    this.pendingRequests.clear();
  }
}

/**
 * Circuit breaker to prevent cascading failures
 */
export class CircuitBreaker {
  private failures = 0;
  private lastFailureTime = 0;
  private state: 'closed' | 'open' | 'half-open' = 'closed';
  
  constructor(
    private readonly failureThreshold: number = 5,
    private readonly resetTimeoutMs: number = 60000
  ) {}

  /**
   * Execute a request with circuit breaker protection
   */
  async execute<T>(fn: () => Promise<T>): Promise<T> {
    // Check if circuit is open
    if (this.state === 'open') {
      const now = Date.now();
      if (now - this.lastFailureTime >= this.resetTimeoutMs) {
        // Try to recover
        this.state = 'half-open';
      } else {
        throw new Error('Circuit breaker is open - too many failures');
      }
    }

    try {
      const result = await fn();
      
      // Success - reset if in half-open state
      if (this.state === 'half-open') {
        this.state = 'closed';
        this.failures = 0;
      }
      
      return result;
    } catch (error) {
      this.failures++;
      this.lastFailureTime = Date.now();

      // Open circuit if threshold reached
      if (this.failures >= this.failureThreshold) {
        this.state = 'open';
        console.error(`Circuit breaker opened after ${this.failures} failures`);
      }

      throw error;
    }
  }

  /**
   * Get current state
   */
  getState(): 'closed' | 'open' | 'half-open' {
    return this.state;
  }

  /**
   * Reset circuit breaker
   */
  reset(): void {
    this.failures = 0;
    this.lastFailureTime = 0;
    this.state = 'closed';
  }
}

/**
 * Rate Limiting Configuration
 * 
 * Defines rate limits for different endpoints and operations.
 * Client limits are MORE restrictive than server limits to provide
 * immediate feedback and reduce unnecessary network calls.
 */
export const RATE_LIMIT_CONFIG = {
  // Client-side limits (proactive)
  CLIENT_CONVERSATION_SAVE: {
    maxRequests: 3,
    windowMs: 10000, // 10 seconds
    rationale: "Prevents rapid-fire saves during UI interactions"
  },
  
  CLIENT_CLAUDE_CHAT: {
    maxRequests: 5,
    windowMs: 60000, // 1 minute
    rationale: "Prevents rapid-fire Claude API calls from draining credits"
  },
  
  // Server-side limits (enforcement)
  SERVER_CONVERSATION_CREATE: {
    maxRequests: 10,
    windowMs: 60000, // 1 minute
    rationale: "Protects against conversation spam"
  },
  
  SERVER_MESSAGE_SAVE: {
    maxRequests: 5,
    windowMs: 10000, // 10 seconds
    rationale: "Protects against message spam while allowing legitimate bursts"
  },
  
  SERVER_CLAUDE_CHAT: {
    maxRequests: 10,
    windowMs: 60000, // 1 minute
    rationale: "Server-side enforcement for Claude API calls to prevent credit drain"
  }
} as const;
