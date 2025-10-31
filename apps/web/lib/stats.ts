type FetchFn = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

const STATS_ENDPOINT = "/api/v1/query/collection/info";

const defaultDelay = (ms: number) =>
  new Promise<void>((resolve) => {
    setTimeout(resolve, ms);
  });

export async function fetchStatsWithDelay(
  fetchFn: FetchFn,
  baseUrl: string,
  waitMs = 1000,
  delayFn: (ms: number) => Promise<void> = defaultDelay,
): Promise<Response> {
  if (waitMs > 0) {
    await delayFn(waitMs);
  }

  return fetchFn(`${baseUrl}${STATS_ENDPOINT}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
    cache: "no-store",
  });
}
