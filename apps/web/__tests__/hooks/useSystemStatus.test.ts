import { renderHook, act } from '@testing-library/react';
import { useSystemStatus } from '@/hooks/useSystemStatus';

// Mock fetch for connectivity check
global.fetch = jest.fn();

describe('useSystemStatus', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it('initializes with empty statuses array', () => {
    const { result } = renderHook(() => useSystemStatus());
    
    expect(result.current.statuses).toEqual([]);
  });

  it('adds a new status message', () => {
    const { result } = renderHook(() => useSystemStatus());
    
    act(() => {
      result.current.addStatus({
        type: 'info',
        message: 'Test message',
      });
    });

    expect(result.current.statuses).toHaveLength(1);
    expect(result.current.statuses[0].type).toBe('info');
    expect(result.current.statuses[0].message).toBe('Test message');
    expect(result.current.statuses[0].id).toBeDefined();
  });

  it('adds error status using showError convenience method', () => {
    const { result } = renderHook(() => useSystemStatus());
    
    act(() => {
      result.current.showError('Error occurred');
    });

    expect(result.current.statuses).toHaveLength(1);
    expect(result.current.statuses[0].type).toBe('error');
    expect(result.current.statuses[0].message).toBe('Error occurred');
  });

  it('adds warning status using showWarning convenience method', () => {
    const { result } = renderHook(() => useSystemStatus());
    
    act(() => {
      result.current.showWarning('Warning message');
    });

    expect(result.current.statuses).toHaveLength(1);
    expect(result.current.statuses[0].type).toBe('warning');
    expect(result.current.statuses[0].message).toBe('Warning message');
  });

  it('adds info status using showInfo convenience method', () => {
    const { result } = renderHook(() => useSystemStatus());
    
    act(() => {
      result.current.showInfo('Info message');
    });

    expect(result.current.statuses).toHaveLength(1);
    expect(result.current.statuses[0].type).toBe('info');
    expect(result.current.statuses[0].message).toBe('Info message');
  });

  it('dismisses a specific status by id', () => {
    const { result } = renderHook(() => useSystemStatus());
    
    act(() => {
      result.current.addStatus({
        type: 'info',
        message: 'Message 1',
      });
      result.current.addStatus({
        type: 'error',
        message: 'Message 2',
      });
    });

    expect(result.current.statuses).toHaveLength(2);

    act(() => {
      result.current.dismissStatus(result.current.statuses[0].id);
    });

    expect(result.current.statuses).toHaveLength(1);
    expect(result.current.statuses[0].message).toBe('Message 2');
  });

  it('clears all statuses', () => {
    const { result } = renderHook(() => useSystemStatus());
    
    act(() => {
      result.current.showError('Error 1');
      result.current.showWarning('Warning 1');
      result.current.showInfo('Info 1');
    });

    expect(result.current.statuses).toHaveLength(3);

    act(() => {
      result.current.clearStatuses();
    });

    expect(result.current.statuses).toHaveLength(0);
  });

  it('auto-dismisses status after specified duration', () => {
    const { result } = renderHook(() => useSystemStatus());
    
    act(() => {
      result.current.addStatus({
        type: 'info',
        message: 'Auto-dismiss message',
        duration: 3000,
      });
    });

    expect(result.current.statuses).toHaveLength(1);

    // Fast-forward time
    act(() => {
      jest.advanceTimersByTime(3000);
    });

    expect(result.current.statuses).toHaveLength(0);
  });

  it('does not auto-dismiss when duration is 0', () => {
    const { result } = renderHook(() => useSystemStatus());
    
    act(() => {
      result.current.addStatus({
        type: 'info',
        message: 'Persistent message',
        duration: 0,
      });
    });

    expect(result.current.statuses).toHaveLength(1);

    // Fast-forward time
    act(() => {
      jest.advanceTimersByTime(10000);
    });

    // Should still be there
    expect(result.current.statuses).toHaveLength(1);
  });

  it('marks status as dismissible by default', () => {
    const { result } = renderHook(() => useSystemStatus());
    
    act(() => {
      result.current.addStatus({
        type: 'info',
        message: 'Test message',
      });
    });

    expect(result.current.statuses[0].dismissible).toBe(true);
  });

  it('allows non-dismissible status when explicitly set', () => {
    const { result } = renderHook(() => useSystemStatus());
    
    act(() => {
      result.current.addStatus({
        type: 'error',
        message: 'Critical error',
        dismissible: false,
      });
    });

    expect(result.current.statuses[0].dismissible).toBe(false);
  });

  it('supports custom CTA in status', () => {
    const { result } = renderHook(() => useSystemStatus());
    const mockAction = jest.fn();
    
    act(() => {
      result.current.addStatus({
        type: 'warning',
        message: 'Action required',
        cta: {
          label: 'Fix Now',
          onClick: mockAction,
        },
      });
    });

    expect(result.current.statuses[0].cta).toBeDefined();
    expect(result.current.statuses[0].cta?.label).toBe('Fix Now');
    
    // Invoke the CTA action
    act(() => {
      result.current.statuses[0].cta?.onClick();
    });

    expect(mockAction).toHaveBeenCalledTimes(1);
  });

  it('generates unique IDs for each status', () => {
    const { result } = renderHook(() => useSystemStatus());
    
    act(() => {
      result.current.showInfo('Message 1');
      result.current.showInfo('Message 2');
      result.current.showInfo('Message 3');
    });

    const ids = result.current.statuses.map(s => s.id);
    const uniqueIds = new Set(ids);

    expect(uniqueIds.size).toBe(3);
  });
});
