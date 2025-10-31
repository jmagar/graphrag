import { render, screen } from '@testing-library/react';
import { CommandItem } from '@/components/input/CommandItem';

describe('CommandItem', () => {
  const defaultProps = {
    command: '/search',
    description: 'Search the web',
    icon: <span>🔍</span>,
    color: 'blue',
    onClick: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders command and description', () => {
    render(<CommandItem {...defaultProps} />);
    
    expect(screen.getByText('/search')).toBeInTheDocument();
    expect(screen.getByText('Search the web')).toBeInTheDocument();
  });

  it('renders icon', () => {
    render(<CommandItem {...defaultProps} />);
    
    expect(screen.getByText('🔍')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    render(<CommandItem {...defaultProps} />);
    
    const button = screen.getByRole('button');
    button.click();
    
    expect(defaultProps.onClick).toHaveBeenCalledTimes(1);
  });

  it('renders as button element', () => {
    render(<CommandItem {...defaultProps} />);
    
    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
  });

  it('applies aria-selected when selected', () => {
    render(<CommandItem {...defaultProps} selected={true} />);
    
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('aria-selected', 'true');
  });

  it('applies aria-selected=false when not selected', () => {
    render(<CommandItem {...defaultProps} selected={false} />);
    
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('aria-selected', 'false');
  });

  it('defaults aria-selected to false', () => {
    render(<CommandItem {...defaultProps} />);
    
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('aria-selected', 'false');
  });

  it('renders with different colors', () => {
    const { rerender } = render(<CommandItem {...defaultProps} color="green" />);
    expect(screen.getByText('/search')).toBeInTheDocument();
    
    rerender(<CommandItem {...defaultProps} color="red" />);
    expect(screen.getByText('/search')).toBeInTheDocument();
  });
});
