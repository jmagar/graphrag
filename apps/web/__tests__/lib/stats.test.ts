import { fetchStatsWithDelay } from "@/lib/stats";

describe("fetchStatsWithDelay", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  it("delays the initial backend request by the configured wait period", async () => {
    const fetchMock = jest.fn().mockResolvedValue({ ok: true });
    const waitMs = 1000;
    const baseUrl = "http://localhost:4400";

    const fetchPromise = fetchStatsWithDelay(fetchMock, baseUrl, waitMs);

    expect(fetchMock).not.toHaveBeenCalled();

    await jest.advanceTimersByTimeAsync(waitMs);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      `${baseUrl}/api/v1/query/collection/info`,
      expect.objectContaining({
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
        cache: "no-store",
      }),
    );

    await expect(fetchPromise).resolves.toEqual({ ok: true });
  });
});
