import { render, screen } from '@testing-library/react';
import { MessageActions } from '@/components/chat/MessageActions';

describe('MessageActions', () => {
  const defaultProps = {
    timestamp: '2:35 PM',
  };

  it('renders timestamp', () => {
    render(<MessageActions {...defaultProps} />);
    
    expect(screen.getByText('2:35 PM')).toBeInTheDocument();
  });

  it('renders reaction button with count', () => {
    render(<MessageActions {...defaultProps} reactions={5} />);
    
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('👍')).toBeInTheDocument();
  });

  it('uses default reaction count', () => {
    render(<MessageActions {...defaultProps} />);
    
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('toggles reaction state on click', () => {
    const { container } = render(<MessageActions {...defaultProps} />);
    
    const reactionButton = container.querySelector('.reaction-btn');
    expect(reactionButton).toBeInTheDocument();
    
    reactionButton?.click();
    // After click, should have reacted class
    expect(reactionButton?.className).toContain('bg-blue-50');
  });

  it('renders copy button', () => {
    render(<MessageActions {...defaultProps} onCopy={jest.fn()} />);
    
    const copyButton = screen.getByTitle('Copy');
    expect(copyButton).toBeInTheDocument();
  });

  it('calls onCopy when copy button is clicked', () => {
    const handleCopy = jest.fn();
    render(<MessageActions {...defaultProps} onCopy={handleCopy} />);
    
    const copyButton = screen.getByTitle('Copy');
    copyButton.click();
    
    expect(handleCopy).toHaveBeenCalledTimes(1);
  });

  it('renders regenerate button when onRegenerate provided', () => {
    render(<MessageActions {...defaultProps} onRegenerate={jest.fn()} />);
    
    const regenerateButton = screen.getByTitle('Regenerate');
    expect(regenerateButton).toBeInTheDocument();
  });

  it('does not render regenerate button when onRegenerate not provided', () => {
    render(<MessageActions {...defaultProps} />);
    
    const regenerateButton = screen.queryByTitle('Regenerate');
    expect(regenerateButton).not.toBeInTheDocument();
  });

  it('calls onRegenerate when regenerate button is clicked', () => {
    const handleRegenerate = jest.fn();
    render(<MessageActions {...defaultProps} onRegenerate={handleRegenerate} />);
    
    const regenerateButton = screen.getByTitle('Regenerate');
    regenerateButton.click();
    
    expect(handleRegenerate).toHaveBeenCalledTimes(1);
  });
});
