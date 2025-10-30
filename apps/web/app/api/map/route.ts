import { NextRequest, NextResponse } from 'next/server';
import axios from 'axios';

const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4400';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    if (!body.url) {
      return NextResponse.json({ error: 'URL is required' }, { status: 400 });
    }

    const response = await axios.post(
      `${backendUrl}/api/v1/map/`,
      {
        url: body.url,
        search: body.search,
        limit: body.limit
      },
      { timeout: 60000 }
    );

    return NextResponse.json(response.data);
  } catch (error: unknown) {
    if (axios.isAxiosError(error)) {
      console.error('Map error:', error.response?.data || error.message);
      return NextResponse.json(
        { error: error.response?.data?.detail || 'Failed to map website' },
        { status: error.response?.status || 500 }
      );
    }
    console.error('Map error:', error);
    return NextResponse.json(
      { error: 'Failed to map website' },
      { status: 500 }
    );
  }
}
