import { render, screen, waitFor } from '@testing-library/react';
import { ResponseStream } from '@/components/ui/response-stream';

describe('ResponseStream Component', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it('renders initially empty', () => {
    const { container } = render(<ResponseStream text="Hello" />);
    
    expect(container.textContent).toBe('');
  });

  it('streams text character by character', async () => {
    render(<ResponseStream text="Hello" speed={100} />);
    
    // Initially empty
    expect(screen.queryByText('Hello')).not.toBeInTheDocument();
    
    // After some time, partial text appears
    jest.advanceTimersByTime(200);
    
    await waitFor(() => {
      const content = document.body.textContent;
      expect(content).toContain('H');
    });
  });

  it('completes streaming after sufficient time', async () => {
    const text = "Test";
    const speed = 100; // 100ms per character
    
    render(<ResponseStream text={text} speed={speed} />);
    
    // Fast-forward past all characters
    jest.advanceTimersByTime(text.length * speed + 100);
    
    await waitFor(() => {
      expect(screen.getByText(text)).toBeInTheDocument();
    });
  });

  it('calls onComplete when streaming finishes', async () => {
    const handleComplete = jest.fn();
    const text = "Done";
    const speed = 50;
    
    render(<ResponseStream text={text} speed={speed} onComplete={handleComplete} />);
    
    // Fast-forward past all characters
    jest.advanceTimersByTime(text.length * speed + 100);
    
    await waitFor(() => {
      expect(handleComplete).toHaveBeenCalled();
    });
  });

  it('handles empty text', () => {
    const { container } = render(<ResponseStream text="" />);
    
    expect(container.textContent).toBe('');
  });

  it('handles long text', async () => {
    const longText = "This is a much longer text that should still stream correctly character by character.";
    const speed = 10;
    
    render(<ResponseStream text={longText} speed={speed} />);
    
    // Fast-forward partially
    jest.advanceTimersByTime(50);
    
    await waitFor(() => {
      const content = document.body.textContent || '';
      expect(content.length).toBeGreaterThan(0);
      expect(content.length).toBeLessThan(longText.length);
    });
  });

  it('applies custom className', () => {
    const { container } = render(
      <ResponseStream text="Styled" className="custom-stream" />
    );
    
    const element = container.firstChild;
    expect(element).toHaveClass('custom-stream');
  });

  it('updates when text prop changes', async () => {
    const { rerender } = render(<ResponseStream text="First" speed={50} />);
    
    jest.advanceTimersByTime(300);
    
    await waitFor(() => {
      expect(screen.getByText('First')).toBeInTheDocument();
    });
    
    // Change text
    rerender(<ResponseStream text="Second" speed={50} />);
    
    jest.advanceTimersByTime(300);
    
    await waitFor(() => {
      expect(screen.getByText('Second')).toBeInTheDocument();
    });
  });

  it('uses default speed when not specified', () => {
    render(<ResponseStream text="Default speed" />);
    
    jest.advanceTimersByTime(100);
    
    // Should have started streaming
    const content = document.body.textContent || '';
    expect(content.length).toBeGreaterThan(0);
  });
});
