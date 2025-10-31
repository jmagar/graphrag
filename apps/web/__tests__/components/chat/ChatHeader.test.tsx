import { render, screen, fireEvent } from '@testing-library/react';
import { ChatHeader } from '@/components/chat/ChatHeader';

// Mock dependencies
jest.mock('@/components/chat/ConversationTabs', () => ({
  ConversationTabs: () => <div data-testid="conversation-tabs">Tabs</div>,
}));

jest.mock('@/components/layout/MobileMenu', () => ({
  MobileMenu: ({ onClick, side }: { onClick: () => void; side: string }) => (
    <button data-testid={`mobile-menu-${side}`} onClick={onClick}>
      Menu {side}
    </button>
  ),
}));

// Mock alert
global.alert = jest.fn();

describe('ChatHeader', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders header title', () => {
    render(<ChatHeader />);
    
    expect(screen.getByText('GraphRAG Configuration')).toBeInTheDocument();
  });

  it('renders source count indicator', () => {
    render(<ChatHeader />);
    
    expect(screen.getByText('3 sources')).toBeInTheDocument();
  });

  it('renders conversation tabs', () => {
    render(<ChatHeader />);
    
    expect(screen.getByTestId('conversation-tabs')).toBeInTheDocument();
  });

  it('renders export button', () => {
    render(<ChatHeader />);
    
    const exportButton = screen.getByLabelText('Export conversation (0 messages)');
    expect(exportButton).toBeInTheDocument();
  });

  it('renders share button', () => {
    render(<ChatHeader />);
    
    const shareButton = screen.getByTitle('Share');
    expect(shareButton).toBeInTheDocument();
  });

  it('disables export button when no messages', () => {
    render(<ChatHeader />);
    
    const exportButton = screen.getByLabelText('Export conversation (0 messages)');
    expect(exportButton).toBeDisabled();
    
    // Disabled button shouldn't trigger alert when clicked
    fireEvent.click(exportButton);
    expect(global.alert).not.toHaveBeenCalled();
  });

  it('exports messages when messages exist', () => {
    const messages = [
      { id: '1', role: 'user' as const, content: 'test question' },
      { id: '2', role: 'assistant' as const, content: 'test answer' },
    ];
    render(<ChatHeader messages={messages} />);
    
    const exportButton = screen.getByLabelText('Export conversation (2 messages)');
    expect(exportButton).not.toBeDisabled();
    
    // Note: Actual export functionality would need to mock exportMessagesToMarkdown
    // For now, we just verify the button is enabled with messages
  });

  it('calls alert when share button clicked', () => {
    render(<ChatHeader />);
    
    const shareButton = screen.getByTitle('Share');
    fireEvent.click(shareButton);
    
    expect(global.alert).toHaveBeenCalledWith('Share functionality - to be implemented');
  });

  it('renders left mobile menu when onLeftMenuClick provided', () => {
    const handleClick = jest.fn();
    render(<ChatHeader onLeftMenuClick={handleClick} />);
    
    expect(screen.getByTestId('mobile-menu-left')).toBeInTheDocument();
  });

  it('does not render left mobile menu when onLeftMenuClick not provided', () => {
    render(<ChatHeader />);
    
    expect(screen.queryByTestId('mobile-menu-left')).not.toBeInTheDocument();
  });

  it('renders right mobile menu when onRightMenuClick provided', () => {
    const handleClick = jest.fn();
    render(<ChatHeader onRightMenuClick={handleClick} />);
    
    expect(screen.getByTestId('mobile-menu-right')).toBeInTheDocument();
  });

  it('does not render right mobile menu when onRightMenuClick not provided', () => {
    render(<ChatHeader />);
    
    expect(screen.queryByTestId('mobile-menu-right')).not.toBeInTheDocument();
  });

  it('calls onLeftMenuClick when left menu clicked', () => {
    const handleClick = jest.fn();
    render(<ChatHeader onLeftMenuClick={handleClick} />);
    
    const leftMenu = screen.getByTestId('mobile-menu-left');
    fireEvent.click(leftMenu);
    
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('calls onRightMenuClick when right menu clicked', () => {
    const handleClick = jest.fn();
    render(<ChatHeader onRightMenuClick={handleClick} />);
    
    const rightMenu = screen.getByTestId('mobile-menu-right');
    fireEvent.click(rightMenu);
    
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('renders status indicator with green dot', () => {
    const { container } = render(<ChatHeader />);
    
    const greenDot = container.querySelector('.bg-emerald-500');
    expect(greenDot).toBeInTheDocument();
  });
});
