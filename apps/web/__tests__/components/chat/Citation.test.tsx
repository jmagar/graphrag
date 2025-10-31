import { render, screen } from '@testing-library/react';
import { Citation } from '@/components/chat/Citation';

describe('Citation', () => {
  it('renders citation with number and title', () => {
    render(<Citation number={1} title="Example Article" />);
    
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('Example Article')).toBeInTheDocument();
  });

  it('renders citation as button', () => {
    render(<Citation number={1} title="Test" />);
    
    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<Citation number={1} title="Test" onClick={handleClick} />);
    
    const button = screen.getByRole('button');
    button.click();
    
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('renders without onClick handler', () => {
    render(<Citation number={1} title="Test" />);
    
    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
  });

  it('displays correct number in badge', () => {
    render(<Citation number={5} title="Test" />);
    
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('renders external link icon', () => {
    const { container } = render(<Citation number={1} title="Test" />);
    
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('handles long titles', () => {
    const longTitle = 'A'.repeat(100);
    render(<Citation number={1} title={longTitle} />);
    
    expect(screen.getByText(longTitle)).toBeInTheDocument();
  });

  it('renders tooltip with url and preview', () => {
    const { container } = render(
      <Citation 
        number={1} 
        title="Test Article" 
        url="https://example.com"
        preview="This is a preview of the article content"
      />
    );
    
    // Verify tooltip container exists
    const tooltip = container.querySelector('.group-hover\\:opacity-100');
    expect(tooltip).toBeInTheDocument();
    
    // Verify tooltip contains the URL
    expect(screen.getByText('https://example.com')).toBeInTheDocument();
    
    // Verify tooltip contains the preview
    expect(screen.getByText('This is a preview of the article content')).toBeInTheDocument();
  });

  it('includes url in aria-label when provided', () => {
    render(
      <Citation 
        number={1} 
        title="Test" 
        url="https://example.com"
      />
    );
    
    const button = screen.getByLabelText(/Citation 1: Test - https:\/\/example\.com/);
    expect(button).toBeInTheDocument();
  });

  it('does not render tooltip when no url or preview', () => {
    const { container } = render(<Citation number={1} title="Test" />);
    
    // Tooltip should not exist without url or preview
    const tooltip = container.querySelector('.group-hover\\:opacity-100');
    expect(tooltip).not.toBeInTheDocument();
  });

  it('renders tooltip with only url', () => {
    const { container } = render(
      <Citation 
        number={1} 
        title="Test" 
        url="https://example.com"
      />
    );
    
    const tooltip = container.querySelector('.group-hover\\:opacity-100');
    expect(tooltip).toBeInTheDocument();
    expect(screen.getByText('https://example.com')).toBeInTheDocument();
  });

  it('renders tooltip with only preview', () => {
    const { container } = render(
      <Citation 
        number={1} 
        title="Test" 
        preview="Just a preview"
      />
    );
    
    const tooltip = container.querySelector('.group-hover\\:opacity-100');
    expect(tooltip).toBeInTheDocument();
    expect(screen.getByText('Just a preview')).toBeInTheDocument();
  });
});
