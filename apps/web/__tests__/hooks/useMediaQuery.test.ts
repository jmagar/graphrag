import { renderHook } from '@testing-library/react';
import { useMediaQuery, useIsMobile, useIsTablet, useIsDesktop } from '@/hooks/useMediaQuery';

// Mock window.matchMedia with proper typing
const createMatchMedia = (matches: boolean): typeof window.matchMedia => {
  return (query: string): MediaQueryList => ({
    matches,
    media: query,
    onchange: null,
    addListener: jest.fn(), // Deprecated
    removeListener: jest.fn(), // Deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  } as MediaQueryList);
};

describe('useMediaQuery', () => {
  beforeEach(() => {
    // Reset mock
    window.matchMedia = createMatchMedia(false);
  });

  it('returns false initially for non-matching query', () => {
    window.matchMedia = createMatchMedia(false);

    const { result } = renderHook(() => useMediaQuery('(max-width: 768px)'));

    expect(result.current).toBe(false);
  });

  it('returns true for matching query', () => {
    window.matchMedia = createMatchMedia(true);

    const { result } = renderHook(() => useMediaQuery('(max-width: 768px)'));

    expect(result.current).toBe(true);
  });

  it('accepts different query strings', () => {
    window.matchMedia = createMatchMedia(true);

    const { result } = renderHook(() => useMediaQuery('(min-width: 1024px)'));

    expect(result.current).toBe(true);
  });
});

describe('useIsMobile', () => {
  it('returns true when screen is mobile size', () => {
    window.matchMedia = createMatchMedia(true);

    const { result } = renderHook(() => useIsMobile());

    expect(result.current).toBe(true);
  });

  it('returns false when screen is not mobile size', () => {
    window.matchMedia = createMatchMedia(false);

    const { result } = renderHook(() => useIsMobile());

    expect(result.current).toBe(false);
  });
});

describe('useIsTablet', () => {
  it('returns appropriate value', () => {
    window.matchMedia = createMatchMedia(false);

    const { result } = renderHook(() => useIsTablet());

    // Should return a boolean
    expect(typeof result.current).toBe('boolean');
  });
});

describe('useIsDesktop', () => {
  it('returns appropriate value', () => {
    window.matchMedia = createMatchMedia(false);

    const { result } = renderHook(() => useIsDesktop());

    // Should return a boolean
    expect(typeof result.current).toBe('boolean');
  });
});
