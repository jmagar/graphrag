import { NextRequest, NextResponse } from 'next/server';
import axios from 'axios';

const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4400';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    if (!body.url || !body.schema) {
      return NextResponse.json(
        { error: 'URL and schema are required' },
        { status: 400 }
      );
    }

    const response = await axios.post(
      `${backendUrl}/api/v1/extract/`,
      {
        url: body.url,
        schema: body.schema,
        formats: body.formats || ['markdown']
      },
      { timeout: 90000 }
    );

    return NextResponse.json(response.data);
  } catch (error: unknown) {
    if (axios.isAxiosError(error)) {
      console.error('Extract error:', error.response?.data || error.message);
      return NextResponse.json(
        { error: error.response?.data?.detail || 'Failed to extract data' },
        { status: error.response?.status || 500 }
      );
    }
    console.error('Extract error:', error);
    return NextResponse.json(
      { error: 'Failed to extract data' },
      { status: 500 }
    );
  }
}
