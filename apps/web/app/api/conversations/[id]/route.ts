/**
 * Single Conversation API Route - Proxy to backend
 * 
 * GET    /api/conversations/[id] - Get conversation with messages
 * PUT    /api/conversations/[id] - Update conversation
 * DELETE /api/conversations/[id] - Delete conversation
 */

import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4400';
const FETCH_TIMEOUT = 30000; // 30 seconds

interface RouteContext {
  params: Promise<{ id: string }>;
}

export async function GET(
  request: NextRequest,
  context: RouteContext
) {
  try {
    const { id } = await context.params;
    const response = await fetch(`${API_BASE}/api/v1/conversations/${id}`, {
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
    console.error('Error fetching conversation:', error);
    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json(
        { error: 'Request timeout' },
        { status: 504 }
      );
    }
    return NextResponse.json(
      { error: 'Failed to fetch conversation' },
      { status: 500 }
    );
  }
}

export async function PUT(
  request: NextRequest,
  context: RouteContext
) {
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
    
    const { id } = await context.params;
    
    const response = await fetch(`${API_BASE}/api/v1/conversations/${id}`, {
      method: 'PUT',
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
    console.error('Error updating conversation:', error);
    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json(
        { error: 'Request timeout' },
        { status: 504 }
      );
    }
    return NextResponse.json(
      { error: 'Failed to update conversation' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  context: RouteContext
) {
  try {
    const { id } = await context.params;
    const response = await fetch(`${API_BASE}/api/v1/conversations/${id}`, {
      method: 'DELETE',
      signal: AbortSignal.timeout(FETCH_TIMEOUT),
    });
    
    // DELETE returns 204 No Content
    if (response.status === 204) {
      return new NextResponse(null, { status: 204 });
    }
    
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
    console.error('Error deleting conversation:', error);
    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json(
        { error: 'Request timeout' },
        { status: 504 }
      );
    }
    return NextResponse.json(
      { error: 'Failed to delete conversation' },
      { status: 500 }
    );
  }
}
