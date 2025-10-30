
import { NextRequest, NextResponse } from 'next/server';
import axios from 'axios';

const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    if (!body.url) {
      return NextResponse.json({ error: 'URL is required' }, { status: 400 });
    }

    // Forward request to FastAPI backend (with trailing slash to avoid 307 redirect)
    const response = await axios.post(
      `${backendUrl}/api/v1/crawl/`,
      body
    );

    return NextResponse.json(response.data);
  } catch (error: any) {
    console.error('Crawl error:', error.response?.data || error.message);
    return NextResponse.json(
      { error: error.response?.data?.detail || 'Failed to start crawl' },
      { status: error.response?.status || 500 }
    );
  }
}
