/**
 * Tests for /api/health endpoint
 * Following TDD approach: RED-GREEN-REFACTOR
 */

// Mock Next.js server components before importing
jest.mock('next/server', () => ({
  NextResponse: class MockNextResponse {
    status: number;
    body: unknown;
    headers: Map<string, string>;

    constructor(body: unknown, init?: { status?: number }) {
      this.body = body;
      this.status = init?.status || 200;
      this.headers = new Map();
    }

    async json() {
      return this.body;
    }

    static json(data: unknown, init?: { status?: number }) {
      return new MockNextResponse(data, init);
    }
  },
}));

// Mock fetch globally
global.fetch = jest.fn();

// Import after mocks are set up
import { GET, HEAD } from '@/app/api/health/route';
import { NextResponse } from 'next/server';

describe('GET /api/health', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset environment variable
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:4400';
  });

  it('returns 200 with backend service info when healthy', async () => {
    // Arrange: Mock healthy backend response
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        status: 'healthy',
        version: '1.0.0',
        services: {
          firecrawl: 'http://localhost:4200',
          qdrant: 'http://localhost:4203',
          tei: 'http://localhost:4207',
        },
      }),
    });

    // Act: Call the GET handler
    const response = await GET();
    const data = await response.json();

    // Assert: Should return 200 with service info
    expect(response.status).toBe(200);
    expect(data.status).toBe('healthy');
    expect(data.version).toBe('1.0.0');
    expect(data.services).toBeDefined();
    expect(data.services.firecrawl).toBeDefined();

    // Verify fetch was called with correct URL
    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:4400/health',
      expect.objectContaining({
        method: 'GET',
        cache: 'no-store',
      })
    );
  });

  it('returns 503 when backend returns non-ok status', async () => {
    // Arrange: Mock unhealthy backend
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: 'Service unavailable' }),
    });

    // Act
    const response = await GET();
    const data = await response.json();

    // Assert: Should return 503
    expect(response.status).toBe(503);
    expect(data.error).toBe('Backend unhealthy');
  });

  it('returns 503 when backend is unreachable', async () => {
    // Arrange: Mock network error
    (global.fetch as jest.Mock).mockRejectedValue(
      new Error('ECONNREFUSED: Connection refused')
    );

    // Act
    const response = await GET();
    const data = await response.json();

    // Assert: Should return 503 with error message
    expect(response.status).toBe(503);
    expect(data.error).toBe('Failed to connect to backend');
  });

  it('uses NEXT_PUBLIC_API_URL environment variable', async () => {
    // Arrange: Set custom API URL
    process.env.NEXT_PUBLIC_API_URL = 'http://custom-backend:8080';
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'healthy' }),
    });

    // Act
    await GET();

    // Assert: Should use custom URL
    expect(global.fetch).toHaveBeenCalledWith(
      'http://custom-backend:8080/health',
      expect.any(Object)
    );
  });

  it('falls back to localhost:4400 when NEXT_PUBLIC_API_URL not set', async () => {
    // Arrange: Remove environment variable
    delete process.env.NEXT_PUBLIC_API_URL;
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'healthy' }),
    });

    // Act
    await GET();

    // Assert: Should use default URL
    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:4400/health',
      expect.any(Object)
    );
  });
});

describe('HEAD /api/health', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:4400';
  });

  it('returns 200 without body when backend is healthy', async () => {
    // Arrange: Mock healthy backend
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: 'healthy' }),
    });

    // Act: Call the HEAD handler
    const response = await HEAD();

    // Assert: Should return 200 with no body
    expect(response.status).toBe(200);
    expect(response.body).toBeNull();
  });

  it('returns 503 without body when backend is unhealthy', async () => {
    // Arrange: Mock unhealthy backend
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 503,
    });

    // Act
    const response = await HEAD();

    // Assert: Should return 503 with no body
    expect(response.status).toBe(503);
    expect(response.body).toBeNull();
  });

  it('returns 503 when backend is unreachable', async () => {
    // Arrange: Mock network error
    (global.fetch as jest.Mock).mockRejectedValue(
      new Error('Network error')
    );

    // Act
    const response = await HEAD();

    // Assert: Should return 503 with no body
    expect(response.status).toBe(503);
    expect(response.body).toBeNull();
  });

  it('makes GET request to backend even for HEAD (conversion)', async () => {
    // Arrange
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'healthy' }),
    });

    // Act
    await HEAD();

    // Assert: Should still use GET method (backend doesn't support HEAD)
    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:4400/health',
      expect.objectContaining({
        method: 'GET',
      })
    );
  });
});
