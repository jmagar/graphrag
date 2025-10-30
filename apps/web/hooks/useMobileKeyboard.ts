"use client";

import { useState, useEffect } from 'react';

export function useMobileKeyboard() {
  const [isKeyboardVisible, setIsKeyboardVisible] = useState(false);

  useEffect(() => {
    const initialHeight = window.visualViewport?.height || window.innerHeight;

    const handleResize = () => {
      const currentHeight = window.visualViewport?.height || window.innerHeight;
      const heightDiff = initialHeight - currentHeight;
      
      // If viewport height decreased by more than 150px, keyboard is likely open
      setIsKeyboardVisible(heightDiff > 150);
    };

    const handleFocus = () => {
      // Small delay to allow viewport to adjust
      setTimeout(() => {
        const currentHeight = window.visualViewport?.height || window.innerHeight;
        const heightDiff = initialHeight - currentHeight;
        setIsKeyboardVisible(heightDiff > 150);
      }, 300);
    };

    const handleBlur = () => {
      setIsKeyboardVisible(false);
    };

    // Listen to visualViewport for more accurate keyboard detection
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', handleResize);
    } else {
      window.addEventListener('resize', handleResize);
    }

    // Also listen to input focus events
    window.addEventListener('focusin', handleFocus);
    window.addEventListener('focusout', handleBlur);

    return () => {
      if (window.visualViewport) {
        window.visualViewport.removeEventListener('resize', handleResize);
      } else {
        window.removeEventListener('resize', handleResize);
      }
      window.removeEventListener('focusin', handleFocus);
      window.removeEventListener('focusout', handleBlur);
    };
  }, []);

  return isKeyboardVisible;
}
