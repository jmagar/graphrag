import { render, screen } from '@testing-library/react';
import { TypingIndicator } from '@/components/chat/TypingIndicator';

// Mock the Avatar component
jest.mock('@/components/chat/Avatar', () => ({
  Avatar: () => <div data-testid="avatar">Avatar</div>,
}));

describe('TypingIndicator', () => {
  it('renders with default message', () => {
    render(<TypingIndicator />);
    
    expect(screen.getByText('Thinking...')).toBeInTheDocument();
  });

  it('renders with custom message', () => {
    render(<TypingIndicator message="Processing your request..." />);
    
    expect(screen.getByText('Processing your request...')).toBeInTheDocument();
  });

  it('renders avatar', () => {
    render(<TypingIndicator />);
    
    expect(screen.getByTestId('avatar')).toBeInTheDocument();
  });

  it('renders three animated dots', () => {
    const { container } = render(<TypingIndicator />);
    
    const dots = container.querySelectorAll('.animate-bounce');
    expect(dots).toHaveLength(3);
  });

  it('has correct animation delays', () => {
    const { container } = render(<TypingIndicator />);
    
    const dots = container.querySelectorAll('.animate-bounce');
    expect(dots[0]).toHaveStyle({ animationDelay: '0ms' });
    expect(dots[1]).toHaveStyle({ animationDelay: '150ms' });
    expect(dots[2]).toHaveStyle({ animationDelay: '300ms' });
  });
});
