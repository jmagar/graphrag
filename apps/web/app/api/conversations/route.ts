/**
 * Conversations API Route - Proxy to backend
 * 
 * GET  /api/conversations - List conversations
 * POST /api/conversations - Create conversation
 */

import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4400';
const FETCH_TIMEOUT = 30000; // 30 seconds

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const queryString = searchParams.toString();
    const url = `${API_BASE}/api/v1/conversations${queryString ? `?${queryString}` : ''}`;
    
    const response = await fetch(url, {
      signal: AbortSignal.timeout(FETCH_TIMEOUT),
    });
    
    let data: unknown;
    try {
      data = await response.json();
    } catch (_parseError) {
      // Safe JSON parsing fallback
      return NextResponse.json(
        { error: 'Invalid response from server' },
        { status: 502 }
      );
    }
    
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error fetching conversations:', error);
    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json(
        { error: 'Request timeout' },
        { status: 504 }
      );
    }
    return NextResponse.json(
      { error: 'Failed to fetch conversations' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    let body: unknown;
    try {
      body = await request.json();
    } catch (_parseError) {
      return NextResponse.json(
        { error: 'Invalid JSON in request body' },
        { status: 400 }
      );
    }
    
    // Validate required fields
    if (typeof body !== 'object' || body === null) {
      return NextResponse.json(
        { error: 'Request body must be an object' },
        { status: 400 }
      );
    }
    
    const bodyObj = body as Record<string, unknown>;
    if (!bodyObj.title || typeof bodyObj.title !== 'string') {
      return NextResponse.json(
        { error: 'title field is required and must be a string' },
        { status: 400 }
      );
    }
    
    const response = await fetch(`${API_BASE}/api/v1/conversations/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(FETCH_TIMEOUT),
    });
    
    let data: unknown;
    try {
      data = await response.json();
    } catch (_parseError) {
      return NextResponse.json(
        { error: 'Invalid response from server' },
        { status: 502 }
      );
    }
    
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error creating conversation:', error);
    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json(
        { error: 'Request timeout' },
        { status: 504 }
      );
    }
    return NextResponse.json(
      { error: 'Failed to create conversation' },
      { status: 500 }
    );
  }
}
