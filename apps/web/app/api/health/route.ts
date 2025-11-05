/**
 * Health Check API route - proxies requests to the FastAPI backend
 * 
 * This endpoint is used by the frontend to check if the backend API is healthy.
 * Supports both GET (full health info) and HEAD (lightweight check) methods.
 */
import { NextResponse } from "next/server";

/**
 * Get the API base URL from environment or use default
 * Read at runtime to support test environment variable changes
 */
function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:4400";
}

/**
 * GET /api/health
 * Returns full health information from the backend
 */
export async function GET() {
  const API_BASE_URL = getApiBaseUrl();
  
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store", // Always get fresh health status
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: "Backend unhealthy", status: response.status },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Health check error:", error);
    return NextResponse.json(
      { error: "Failed to connect to backend" },
      { status: 503 }
    );
  }
}

/**
 * HEAD /api/health
 * Lightweight health check that returns only status code (no body)
 * Used by useSystemStatus hook for periodic connectivity checks
 */
export async function HEAD() {
  const API_BASE_URL = getApiBaseUrl();
  
  try {
    // Backend only supports GET, so we make a GET request but don't return the body
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store",
    });

    // Return empty response with appropriate status code
    return new NextResponse(null, {
      status: response.ok ? 200 : 503,
    });
  } catch (error) {
    console.error("Health check error:", error);
    return new NextResponse(null, { status: 503 });
  }
}
