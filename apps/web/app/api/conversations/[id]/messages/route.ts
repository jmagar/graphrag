/**
 * Conversation Messages API Route - Proxy to backend
 * 
 * POST /api/conversations/[id]/messages - Add message to conversation
 */

import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4400';
const FETCH_TIMEOUT = 30000; // 30 seconds

interface RouteContext {
  params: Promise<{ id: string }>;
}

export async function POST(request: NextRequest, context: RouteContext) {
  try {
    const { id } = await context.params;
    
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
    if (!bodyObj.role || typeof bodyObj.role !== 'string') {
      return NextResponse.json(
        { error: 'role field is required and must be a string' },
        { status: 400 }
      );
    }
    
    if (!bodyObj.content || typeof bodyObj.content !== 'string') {
      return NextResponse.json(
        { error: 'content field is required and must be a string' },
        { status: 400 }
      );
    }
    
    const response = await fetch(`${API_BASE}/api/v1/conversations/${id}/messages`, {
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
    console.error('Error adding message to conversation:', error);
    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json(
        { error: 'Request timeout' },
        { status: 504 }
      );
    }
    return NextResponse.json(
      { error: 'Failed to add message' },
      { status: 500 }
    );
  }
}
