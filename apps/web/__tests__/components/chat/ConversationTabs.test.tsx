import { render, screen, fireEvent } from '@testing-library/react';
import { ConversationTabs } from '@/components/chat/ConversationTabs';

describe('ConversationTabs', () => {
  it('renders all tab buttons', () => {
    render(<ConversationTabs />);
    
    expect(screen.getByText('Chat')).toBeInTheDocument();
    expect(screen.getByText('Sources')).toBeInTheDocument();
    expect(screen.getByText('Graph')).toBeInTheDocument();
    expect(screen.getByText('Pins')).toBeInTheDocument();
    expect(screen.getByText('Composer')).toBeInTheDocument();
    expect(screen.getByText('Explore')).toBeInTheDocument();
  });

  it('sets Chat as active tab by default', () => {
    const { container } = render(<ConversationTabs />);
    
    const chatButton = screen.getByText('Chat').closest('button');
    expect(chatButton?.className).toContain('text-blue-600');
  });

  it('opens dropdown when tab is clicked', () => {
    render(<ConversationTabs />);
    
    const chatButton = screen.getByText('Chat');
    fireEvent.click(chatButton);
    
    // Should show dropdown items
    expect(screen.getByText('New Chat')).toBeInTheDocument();
    expect(screen.getByText('Start a new conversation')).toBeInTheDocument();
  });

  it('shows correct dropdown items for Sources tab', () => {
    render(<ConversationTabs />);
    
    const sourcesButton = screen.getByText('Sources');
    fireEvent.click(sourcesButton);
    
    expect(screen.getByText('Add Source')).toBeInTheDocument();
    expect(screen.getByText('Connect URL')).toBeInTheDocument();
  });

  it('shows correct dropdown items for Graph tab', () => {
    render(<ConversationTabs />);
    
    const graphButton = screen.getByText('Graph');
    fireEvent.click(graphButton);
    
    expect(screen.getByText('View Graph')).toBeInTheDocument();
    expect(screen.getByText('Search Nodes')).toBeInTheDocument();
  });

  it('closes dropdown when clicking tab again', () => {
    render(<ConversationTabs />);
    
    const chatButton = screen.getByText('Chat');
    
    // Open dropdown
    fireEvent.click(chatButton);
    expect(screen.getByText('New Chat')).toBeInTheDocument();
    
    // Close dropdown
    fireEvent.click(chatButton);
    expect(screen.queryByText('New Chat')).not.toBeInTheDocument();
  });

  it('switches active tab when different tab clicked', () => {
    render(<ConversationTabs />);
    
    const sourcesButton = screen.getByText('Sources');
    fireEvent.click(sourcesButton);
    
    expect(sourcesButton.closest('button')?.className).toContain('text-blue-600');
  });

  it('renders dropdown icons', () => {
    render(<ConversationTabs />);
    
    const chatButton = screen.getByText('Chat');
    fireEvent.click(chatButton);
    
    expect(screen.getByText('💬')).toBeInTheDocument();
    expect(screen.getByText('📋')).toBeInTheDocument();
  });

  it('renders chevron down icon for all tabs', () => {
    const { container } = render(<ConversationTabs />);
    
    const chevrons = container.querySelectorAll('svg');
    // Should have 6 chevrons (one per tab)
    expect(chevrons.length).toBeGreaterThanOrEqual(6);
  });

  it('renders Composer tab with multiple dropdown items', () => {
    render(<ConversationTabs />);
    
    const composerButton = screen.getByText('Composer');
    fireEvent.click(composerButton);
    
    expect(screen.getByText('New Document')).toBeInTheDocument();
    expect(screen.getByText('Templates')).toBeInTheDocument();
    expect(screen.getByText('Rich Editor')).toBeInTheDocument();
  });

  it('renders Explore tab dropdown', () => {
    render(<ConversationTabs />);
    
    const exploreButton = screen.getByText('Explore');
    fireEvent.click(exploreButton);
    
    expect(screen.getByText('Discover')).toBeInTheDocument();
    expect(screen.getByText('Deep Dive')).toBeInTheDocument();
  });

  it('renders Pins tab dropdown', () => {
    render(<ConversationTabs />);
    
    const pinsButton = screen.getByText('Pins');
    fireEvent.click(pinsButton);
    
    expect(screen.getByText('Pinned Items')).toBeInTheDocument();
    expect(screen.getByText('Favorites')).toBeInTheDocument();
  });
});
