"use client";

import { useState, useEffect } from 'react';

export function useMediaQuery(query: string): boolean {
  // Initialize with a function that runs once
  const getMatches = (query: string): boolean => {
    if (typeof window !== 'undefined') {
      return window.matchMedia(query).matches;
    }
    return false;
  };

  const [matches, setMatches] = useState(() => getMatches(query));

  useEffect(() => {
    const media = window.matchMedia(query);
    
    // Create listener that updates state when media query changes
    const listener = (e: MediaQueryListEvent) => setMatches(e.matches);
    
    // Trigger listener immediately with current state to sync on query change
    listener({ matches: media.matches } as MediaQueryListEvent);
    
    // Add listener (modern browsers)
    if (media.addEventListener) {
      media.addEventListener('change', listener);
      return () => media.removeEventListener('change', listener);
    } else {
      // Fallback for older browsers
      media.addListener(listener);
      return () => media.removeListener(listener);
    }
  }, [query]);

  return matches;
}

// Convenience hooks for common breakpoints
export function useIsMobile() {
  return useMediaQuery('(max-width: 767px)');
}

export function useIsTablet() {
  return useMediaQuery('(min-width: 768px) and (max-width: 1023px)');
}

export function useIsDesktop() {
  return useMediaQuery('(min-width: 1024px)');
}
