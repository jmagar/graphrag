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
  private timestamps: number[] = [];
  private pendingRequests = new Map<string, Promise<unknown>>();
  private config: RateLimitConfig;

  constructor(config: RateLimitConfig) {
    this.config = config;
  }

  /**
   * Check if request is allowed
   */
  canMakeRequest(): boolean {
    const now = Date.now();
    const cutoff = now - this.config.windowMs;

    // Remove old timestamps
    this.timestamps = this.timestamps.filter(ts => ts > cutoff);

    // Check if under limit
    return this.timestamps.length < this.config.maxRequests;
  }

  /**
   * Record a request
   */
  recordRequest(): void {
    this.timestamps.push(Date.now());
  }

  /**
   * Get time until next request is allowed
   */
  getRetryAfter(): number {
    if (this.canMakeRequest()) return 0;

    const oldestTimestamp = this.timestamps[0];
    const resetTime = oldestTimestamp + this.config.windowMs;
    return Math.ceil((resetTime - Date.now()) / 1000);
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
    this.timestamps = [];
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
