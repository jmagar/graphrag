import { useState, useCallback, useEffect, useRef } from 'react';

export type SystemMessageType = 'info' | 'warning' | 'error';

export interface SystemStatus {
  id: string;
  type: SystemMessageType;
  message: string;
  dismissible?: boolean;
  duration?: number; // auto-dismiss after ms (0 = no auto-dismiss)
  cta?: {
    label: string;
    onClick: () => void;
  };
}

/**
 * Hook to manage system status messages in the chat
 * Handles API connection status, rate limits, warnings, etc.
 */
export function useSystemStatus() {
  const [statuses, setStatuses] = useState<SystemStatus[]>([]);
  const timersRef = useRef<Map<string, NodeJS.Timeout>>(new Map());

  // Dismiss a specific status (declared first to avoid hoisting issues)
  const dismissStatus = useCallback((id: string) => {
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
    setStatuses((prev) => prev.filter((s) => s.id !== id));
  }, []);

  // Add a new system message
  const addStatus = useCallback((status: Omit<SystemStatus, 'id'>) => {
    const id = `status-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const newStatus: SystemStatus = {
      ...status,
      id,
      dismissible: status.dismissible !== false,
      duration: status.duration ?? 0, // 0 = never auto-dismiss
    };

    setStatuses((prev) => [...prev, newStatus]);

    // Auto-dismiss if duration specified
    if (newStatus.duration && newStatus.duration > 0) {
      const timer = setTimeout(() => {
        dismissStatus(id);
        timersRef.current.delete(id);
      }, newStatus.duration);
      timersRef.current.set(id, timer);
    }
  }, [dismissStatus]);

  // Clear all statuses
  const clearStatuses = useCallback(() => {
    setStatuses([]);
  }, []);

  // Convenience methods for common status types
  const showError = useCallback(
    (message: string, options?: Omit<SystemStatus, 'id' | 'type' | 'message'>) => {
      addStatus({
        type: 'error',
        message,
        ...options,
      });
    },
    [addStatus]
  );

  const showWarning = useCallback(
    (message: string, options?: Omit<SystemStatus, 'id' | 'type' | 'message'>) => {
      addStatus({
        type: 'warning',
        message,
        ...options,
      });
    },
    [addStatus]
  );

  const showInfo = useCallback(
    (message: string, options?: Omit<SystemStatus, 'id' | 'type' | 'message'>) => {
      addStatus({
        type: 'info',
        message,
        ...options,
      });
    },
    [addStatus]
  );

  // Check API connectivity on mount
  useEffect(() => {
    const checkConnectivity = async () => {
      try {
        const response = await fetch('/api/health', { method: 'HEAD' });
        if (!response.ok) {
          showError('API connection lost. Some features may be unavailable.', {
            dismissible: true,
          });
        }
      } catch (error) {
        showError('Unable to connect to API. Check your internet connection.', {
          dismissible: true,
        });
      }
    };

    checkConnectivity();
  }, [showError]);

  // Cleanup all timers on unmount
  useEffect(() => {
    return () => {
      timersRef.current.forEach((timer) => clearTimeout(timer));
      timersRef.current.clear();
    };
  }, []);

  return {
    statuses,
    addStatus,
    dismissStatus,
    clearStatuses,
    showError,
    showWarning,
    showInfo,
  };
}
