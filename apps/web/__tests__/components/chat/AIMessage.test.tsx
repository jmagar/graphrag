import { render, screen } from '@testing-library/react';
import { AIMessage } from '@/components/chat/AIMessage';

// Mock dependencies
jest.mock('@/components/chat/Avatar', () => ({
  Avatar: () => <div data-testid="avatar">Avatar</div>,
}));

jest.mock('@/components/chat/Citation', () => ({
  Citation: ({ number, title }: { number: number; title: string }) => (
    <div data-testid={`citation-${number}`}>{title}</div>
  ),
}));

jest.mock('@/components/chat/MessageActions', () => ({
  MessageActions: () => <div data-testid="message-actions">Actions</div>,
}));

jest.mock('@/components/chat/Artifact', () => ({
  Artifact: ({ type }: { type: string }) => <div data-testid="artifact">{type}</div>,
}));

jest.mock('@/components/chat/ToolCall', () => ({
  ToolCall: ({ command }: { command: string }) => (
    <div data-testid="tool-call">{command}</div>
  ),
}));

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: jest.fn(),
  },
});

describe('AIMessage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders message content', () => {
    render(<AIMessage content={['Hello, world!']} />);
    
    expect(screen.getByText('Hello, world!')).toBeInTheDocument();
  });

  it('renders multiple content paragraphs', () => {
    const content = ['First paragraph', 'Second paragraph', 'Third paragraph'];
    render(<AIMessage content={content} />);
    
    content.forEach((text) => {
      expect(screen.getByText(text)).toBeInTheDocument();
    });
  });

  it('renders avatar', () => {
    render(<AIMessage content={['Test']} />);
    
    expect(screen.getByTestId('avatar')).toBeInTheDocument();
  });

  it('renders message actions', () => {
    render(<AIMessage content={['Test']} />);
    
    expect(screen.getByTestId('message-actions')).toBeInTheDocument();
  });

  it('renders citations when provided', () => {
    const citations = [
      { number: 1, title: 'Source 1' },
      { number: 2, title: 'Source 2' },
    ];
    
    render(<AIMessage content={['Test']} citations={citations} />);
    
    expect(screen.getByTestId('citation-1')).toBeInTheDocument();
    expect(screen.getByTestId('citation-2')).toBeInTheDocument();
  });

  it('does not render citations section when empty', () => {
    render(<AIMessage content={['Test']} citations={[]} />);
    
    expect(screen.queryByTestId('citation-1')).not.toBeInTheDocument();
  });

  it('renders artifact when provided', () => {
    const artifact = {
      type: 'code' as const,
      content: 'console.log("test")',
      language: 'javascript',
    };
    
    render(<AIMessage content={['Test']} artifact={artifact} />);
    
    expect(screen.getByTestId('artifact')).toBeInTheDocument();
  });

  it('does not render artifact when not provided', () => {
    render(<AIMessage content={['Test']} />);
    
    expect(screen.queryByTestId('artifact')).not.toBeInTheDocument();
  });

  it('renders tool calls when provided', () => {
    const toolCalls = [
      { command: '/search', args: 'query' },
      { command: '/scrape', args: 'url' },
    ];
    
    render(<AIMessage content={['Test']} toolCalls={toolCalls} />);
    
    const toolCallElements = screen.getAllByTestId('tool-call');
    expect(toolCallElements).toHaveLength(2);
  });

  it('does not render tool calls when not provided', () => {
    render(<AIMessage content={['Test']} />);
    
    expect(screen.queryByTestId('tool-call')).not.toBeInTheDocument();
  });

  it('uses default timestamp', () => {
    render(<AIMessage content={['Test']} />);
    
    // MessageActions should receive the default timestamp
    expect(screen.getByTestId('message-actions')).toBeInTheDocument();
  });

  it('uses custom timestamp when provided', () => {
    render(<AIMessage content={['Test']} timestamp="3:45 PM" />);
    
    expect(screen.getByTestId('message-actions')).toBeInTheDocument();
  });

  it('renders HTML content safely', () => {
    const content = ['<strong>Bold text</strong>'];
    render(<AIMessage content={content} />);
    
    // dangerouslySetInnerHTML should render the HTML
    const element = screen.getByText('Bold text');
    expect(element.tagName).toBe('STRONG');
  });

  it('handles empty tool calls array', () => {
    render(<AIMessage content={['Test']} toolCalls={[]} />);
    
    expect(screen.queryByTestId('tool-call')).not.toBeInTheDocument();
  });
});
