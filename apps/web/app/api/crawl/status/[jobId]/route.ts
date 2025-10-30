
import { NextRequest, NextResponse } from 'next/server';
import axios from 'axios';

const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4400';

export async function GET(req: NextRequest, { params }: { params: Promise<{ jobId: string }> }) {
  try {
    // Next.js 15: params is now a Promise and must be awaited
    const { jobId } = await params;
    
    // Forward request to FastAPI backend
    const response = await axios.get(`${backendUrl}/api/v1/crawl/${jobId}`);

    return NextResponse.json(response.data);
  } catch (error: unknown) {
    if (axios.isAxiosError(error)) {
      console.error('Status error:', error.response?.data || error.message);
      return NextResponse.json(
        { error: error.response?.data?.detail || 'Failed to get crawl status' },
        { status: error.response?.status || 500 }
      );
    }
    const errorMessage = error instanceof Error ? error.message : 'Failed to get crawl status';
    console.error('Status error:', errorMessage);
    return NextResponse.json(
      { error: errorMessage },
      { status: 500 }
    );
  }
}
