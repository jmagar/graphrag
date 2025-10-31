"use client";

import { useState, useEffect, useRef } from 'react';

interface KeyboardConfig {
  heightThresholdPx?: number;
  heightThresholdPercent?: number;
  stabilizationDelayMs?: number;
  blurDebounceMs?: number;
}

export function useMobileKeyboard(config: KeyboardConfig = {}): boolean {
  const {
    heightThresholdPx = 150,
    heightThresholdPercent = 0.2,
    stabilizationDelayMs = 500,
    blurDebounceMs = 200,
  } = config;

  const [isKeyboardVisible, setIsKeyboardVisible] = useState<boolean>(false);
  const initialHeightRef = useRef<number | null>(null);
  const focusTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const blurTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const orientationChangeTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Initialize keyboard state on mount
    const initializeKeyboardState = () => {
      const currentHeight = window.visualViewport?.height || window.innerHeight;
      initialHeightRef.current = currentHeight;
    };

    initializeKeyboardState();

    const handleResize = () => {
      const currentHeight = window.visualViewport?.height || window.innerHeight;
      const initialHeight = initialHeightRef.current || currentHeight;
      const heightDiff = initialHeight - currentHeight;

      // Calculate threshold as max of absolute px or percentage-based
      const percentThreshold = initialHeight * heightThresholdPercent;
      const threshold = Math.max(heightThresholdPx, percentThreshold);

      // If viewport height decreased by more than threshold, keyboard is likely open
      setIsKeyboardVisible(heightDiff > threshold);
    };

    const handleFocus = () => {
      // Clear any pending blur timeout
      if (blurTimeoutRef.current) {
        clearTimeout(blurTimeoutRef.current);
        blurTimeoutRef.current = null;
      }

      // Small delay to allow viewport to adjust
      if (focusTimeoutRef.current) {
        clearTimeout(focusTimeoutRef.current);
      }

      focusTimeoutRef.current = setTimeout(() => {
        const currentHeight = window.visualViewport?.height || window.innerHeight;
        const initialHeight = initialHeightRef.current || currentHeight;
        const heightDiff = initialHeight - currentHeight;

        const percentThreshold = initialHeight * heightThresholdPercent;
        const threshold = Math.max(heightThresholdPx, percentThreshold);

        setIsKeyboardVisible(heightDiff > threshold);
        focusTimeoutRef.current = null;
      }, 300);
    };

    const handleBlur = () => {
      // Debounce blur to avoid immediate state flip
      if (blurTimeoutRef.current) {
        clearTimeout(blurTimeoutRef.current);
      }

      blurTimeoutRef.current = setTimeout(() => {
        setIsKeyboardVisible(false);
        blurTimeoutRef.current = null;
      }, blurDebounceMs);
    };

    const handleOrientationChange = () => {
      // Reset baseline on orientation change and wait for stabilization
      if (orientationChangeTimeoutRef.current) {
        clearTimeout(orientationChangeTimeoutRef.current);
      }

      orientationChangeTimeoutRef.current = setTimeout(() => {
        const newHeight = window.visualViewport?.height || window.innerHeight;
        initialHeightRef.current = newHeight;
        setIsKeyboardVisible(false);
        orientationChangeTimeoutRef.current = null;
      }, stabilizationDelayMs);
    };

    // Listen to visualViewport for more accurate keyboard detection
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', handleResize);
    } else {
      window.addEventListener('resize', handleResize);
    }

    // Listen to input focus events
    window.addEventListener('focusin', handleFocus);
    window.addEventListener('focusout', handleBlur);

    // Listen to orientation changes
    window.addEventListener('orientationchange', handleOrientationChange);

    return () => {
      // Clean up all timeouts
      if (focusTimeoutRef.current) {
        clearTimeout(focusTimeoutRef.current);
      }
      if (blurTimeoutRef.current) {
        clearTimeout(blurTimeoutRef.current);
      }
      if (orientationChangeTimeoutRef.current) {
        clearTimeout(orientationChangeTimeoutRef.current);
      }

      // Remove event listeners
      if (window.visualViewport) {
        window.visualViewport.removeEventListener('resize', handleResize);
      } else {
        window.removeEventListener('resize', handleResize);
      }
      window.removeEventListener('focusin', handleFocus);
      window.removeEventListener('focusout', handleBlur);
      window.removeEventListener('orientationchange', handleOrientationChange);
    };
  }, [heightThresholdPx, heightThresholdPercent, stabilizationDelayMs, blurDebounceMs]);

  return isKeyboardVisible;
}
