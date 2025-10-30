import { NextRequest, NextResponse } from 'next/server';
import axios from 'axios';

const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    if (!body.url) {
      return NextResponse.json({ error: 'URL is required' }, { status: 400 });
    }

    // Call backend scrape endpoint
    const response = await axios.post(
      `${backendUrl}/api/v1/scrape/`,
      {
        url: body.url,
        formats: body.formats || ['markdown', 'html']
      },
      { timeout: 60000 } // 60 second timeout for scraping
    );

    return NextResponse.json(response.data);
  } catch (error: any) {
    console.error('Scrape error:', error.response?.data || error.message);
    return NextResponse.json(
      { error: error.response?.data?.detail || 'Failed to scrape URL' },
      { status: error.response?.status || 500 }
    );
  }
}
