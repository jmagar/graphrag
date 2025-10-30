import { NextRequest, NextResponse } from 'next/server';
import axios from 'axios';

const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    if (!body.query) {
      return NextResponse.json({ error: 'Query is required' }, { status: 400 });
    }

    const response = await axios.post(
      `${backendUrl}/api/v1/search`,
      {
        query: body.query,
        limit: body.limit || 5,
        formats: body.formats || ['markdown']
      },
      { timeout: 60000 }
    );

    return NextResponse.json(response.data);
  } catch (error: any) {
    console.error('Search error:', error.response?.data || error.message);
    return NextResponse.json(
      { error: error.response?.data?.detail || 'Failed to search' },
      { status: error.response?.status || 500 }
    );
  }
}
