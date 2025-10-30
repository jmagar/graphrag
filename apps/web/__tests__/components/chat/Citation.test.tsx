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
});
