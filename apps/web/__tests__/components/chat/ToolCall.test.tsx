import { render, screen } from '@testing-library/react';
import { ToolCall } from '@/components/chat/ToolCall';

describe('ToolCall', () => {
  it('renders command with slash prefix', () => {
    render(<ToolCall command="/search" />);
    
    expect(screen.getByText('/search')).toBeInTheDocument();
  });

  it('renders command without slash prefix', () => {
    render(<ToolCall command="crawl" />);
    
    expect(screen.getByText('/crawl')).toBeInTheDocument();
  });

  it('renders arguments when provided', () => {
    render(<ToolCall command="/search" args="graphrag implementation" />);
    
    expect(screen.getByText('/search')).toBeInTheDocument();
    expect(screen.getByText('graphrag implementation')).toBeInTheDocument();
  });

  it('renders without arguments', () => {
    render(<ToolCall command="/help" />);
    
    expect(screen.getByText('/help')).toBeInTheDocument();
  });

  it('renders icon for crawl command', () => {
    const { container } = render(<ToolCall command="/crawl" />);
    
    const icon = container.querySelector('svg');
    expect(icon).toBeInTheDocument();
  });

  it('renders icon for scrape command', () => {
    const { container } = render(<ToolCall command="/scrape" />);
    
    const icon = container.querySelector('svg');
    expect(icon).toBeInTheDocument();
  });

  it('renders icon for search command', () => {
    const { container } = render(<ToolCall command="/search" />);
    
    const icon = container.querySelector('svg');
    expect(icon).toBeInTheDocument();
  });

  it('renders default icon for unknown command', () => {
    const { container } = render(<ToolCall command="/unknown" />);
    
    const icon = container.querySelector('svg');
    expect(icon).toBeInTheDocument();
  });

  it('strips leading slash from command name', () => {
    render(<ToolCall command="/test" />);
    
    // Should display as /test (adds it back in display)
    expect(screen.getByText('/test')).toBeInTheDocument();
  });

  it('handles long arguments', () => {
    const longArgs = 'A'.repeat(200);
    render(<ToolCall command="/search" args={longArgs} />);
    
    expect(screen.getByText(longArgs)).toBeInTheDocument();
  });
});
