/**
 * Stats API route - proxies requests to the FastAPI backend
 */
import { NextResponse } from "next/server";
import { fetchStatsWithDelay } from "@/lib/stats";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:4400";
const INITIAL_WAIT_MS = 1000;

export async function GET() {
  try {
    const response = await fetchStatsWithDelay(fetch, API_BASE_URL, INITIAL_WAIT_MS);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: "Unknown error" }));
      return NextResponse.json(
        { error: errorData.detail || "Failed to fetch statistics" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Stats API error:", error);
    return NextResponse.json(
      { error: "Failed to connect to backend service" },
      { status: 500 }
    );
  }
}
