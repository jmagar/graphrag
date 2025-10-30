import { render, screen } from '@testing-library/react';
import { UserMessage } from '@/components/chat/UserMessage';

// Mock the Avatar component
jest.mock('@/components/chat/Avatar', () => ({
  Avatar: () => <div data-testid="avatar">Avatar</div>,
}));

// Mock the ToolCall component
jest.mock('@/components/chat/ToolCall', () => ({
  ToolCall: ({ command, args }: { command: string; args: string }) => (
    <div data-testid="tool-call">
      {command} {args}
    </div>
  ),
}));

describe('UserMessage', () => {
  it('renders user message with content', () => {
    render(<UserMessage content="Hello, world!" />);
    
    expect(screen.getByText('Hello, world!')).toBeInTheDocument();
  });

  it('renders avatar', () => {
    render(<UserMessage content="Test message" />);
    
    expect(screen.getByTestId('avatar')).toBeInTheDocument();
  });

  it('displays timestamp', () => {
    render(<UserMessage content="Test" timestamp="3:45 PM" />);
    
    expect(screen.getByText('3:45 PM')).toBeInTheDocument();
  });

  it('uses default timestamp when not provided', () => {
    render(<UserMessage content="Test" />);
    
    expect(screen.getByText('2:35 PM')).toBeInTheDocument();
  });

  it('renders edit button when onEdit is provided', () => {
    const handleEdit = jest.fn();
    render(<UserMessage content="Test" onEdit={handleEdit} />);
    
    const editButton = screen.getByRole('button', { name: /edit/i });
    expect(editButton).toBeInTheDocument();
  });

  it('does not render edit button when onEdit is not provided', () => {
    render(<UserMessage content="Test" />);
    
    const editButton = screen.queryByRole('button', { name: /edit/i });
    expect(editButton).not.toBeInTheDocument();
  });

  it('calls onEdit when edit button is clicked', () => {
    const handleEdit = jest.fn();
    render(<UserMessage content="Test" onEdit={handleEdit} />);
    
    const editButton = screen.getByRole('button', { name: /edit/i });
    editButton.click();
    
    expect(handleEdit).toHaveBeenCalledTimes(1);
  });

  it('parses slash commands', () => {
    render(<UserMessage content="/search graphrag" />);
    
    // Should render ToolCall component instead of regular message
    expect(screen.getByTestId('tool-call')).toBeInTheDocument();
    expect(screen.getByText('/search graphrag')).toBeInTheDocument();
  });

  it('renders regular message when not a command', () => {
    render(<UserMessage content="Regular message" />);
    
    // Should NOT render ToolCall component
    expect(screen.queryByTestId('tool-call')).not.toBeInTheDocument();
    expect(screen.getByText('Regular message')).toBeInTheDocument();
  });

  it('parses command with arguments', () => {
    render(<UserMessage content="/scrape https://example.com" />);
    
    expect(screen.getByTestId('tool-call')).toBeInTheDocument();
  });

  it('handles command without arguments', () => {
    render(<UserMessage content="/help" />);
    
    expect(screen.getByTestId('tool-call')).toBeInTheDocument();
  });
});
