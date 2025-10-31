import { NextRequest, NextResponse } from 'next/server';
import axios from 'axios';

const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4400';
const FETCH_TIMEOUT = 30000; // 30 seconds

export async function POST(req: NextRequest) {
  try {
    let body: unknown;
    try {
      body = await req.json();
    } catch (_parseError) {
      return NextResponse.json(
        { error: 'Invalid JSON in request body' },
        { status: 400 }
      );
    }
    
    if (typeof body !== 'object' || body === null) {
      return NextResponse.json(
        { error: 'Request body must be an object' },
        { status: 400 }
      );
    }
    
    const bodyObj = body as Record<string, unknown>;

    if (!bodyObj.query || typeof bodyObj.query !== 'string') {
      return NextResponse.json(
        { error: 'query field is required and must be a string' },
        { status: 400 }
      );
    }
    
    // Validate and clamp limit (1-100)
    let limit = 5;
    if (bodyObj.limit !== undefined) {
      if (typeof bodyObj.limit === 'number' && Number.isInteger(bodyObj.limit)) {
        limit = Math.max(1, Math.min(100, bodyObj.limit));
      }
    }
    
    // Validate formats is array of strings
    let formats: string[] = ['markdown'];
    if (bodyObj.formats !== undefined) {
      if (Array.isArray(bodyObj.formats) && bodyObj.formats.every(f => typeof f === 'string')) {
        formats = bodyObj.formats as string[];
      }
    }

    const response = await axios.post(
      `${backendUrl}/api/v1/search/`,
      {
        query: bodyObj.query,
        limit,
        formats
      },
      { timeout: FETCH_TIMEOUT }
    );

    return NextResponse.json(response.data);
  } catch (error: unknown) {
    if (axios.isAxiosError(error)) {
      console.error('Search error:', error.response?.data || error.message);
      return NextResponse.json(
        { error: error.response?.data?.detail || 'Failed to search' },
        { status: error.response?.status || 500 }
      );
    }
    console.error('Search error:', error);
    return NextResponse.json(
      { error: 'Failed to search' },
      { status: 500 }
    );
  }
}
