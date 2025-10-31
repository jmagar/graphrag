import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:4400';
const FETCH_TIMEOUT = 30000; // 30 seconds

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  try {
    const { jobId } = await params;
    
    // Validate jobId is not empty
    if (!jobId || typeof jobId !== 'string') {
      return NextResponse.json(
        { error: 'Invalid jobId' },
        { status: 400 }
      );
    }

    const response = await fetch(`${BACKEND_URL}/api/v1/crawl/${jobId}`, {
      method: 'DELETE',
      signal: AbortSignal.timeout(FETCH_TIMEOUT),
    });

    if (!response.ok) {
      let errorDetail: unknown;
      try {
        errorDetail = await response.json();
      } catch (_parseError) {
        return NextResponse.json(
          { error: 'Failed to cancel crawl' },
          { status: response.status }
        );
      }
      
      const errorObj = errorDetail as Record<string, unknown>;
      return NextResponse.json(
        { error: errorObj.detail || 'Failed to cancel crawl' },
        { status: response.status }
      );
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
    
    return NextResponse.json(data);
  } catch (error: unknown) {
    console.error('Cancel crawl error:', error);
    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json(
        { error: 'Request timeout' },
        { status: 504 }
      );
    }
    const errorMessage = error instanceof Error ? error.message : 'Failed to cancel crawl';
    return NextResponse.json(
      { error: errorMessage },
      { status: 500 }
    );
  }
}
