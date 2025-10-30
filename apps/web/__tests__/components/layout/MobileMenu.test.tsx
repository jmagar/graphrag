import { render, screen, fireEvent } from '@testing-library/react';
import { MobileMenu } from '@/components/layout/MobileMenu';

describe('MobileMenu', () => {
  it('renders menu button', () => {
    const handleClick = jest.fn();
    render(<MobileMenu onClick={handleClick} />);
    
    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<MobileMenu onClick={handleClick} />);
    
    const button = screen.getByRole('button');
    fireEvent.click(button);
    
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('has correct aria-label for left side', () => {
    const handleClick = jest.fn();
    render(<MobileMenu onClick={handleClick} side="left" />);
    
    expect(screen.getByLabelText('Open sidebar')).toBeInTheDocument();
  });

  it('has correct aria-label for right side', () => {
    const handleClick = jest.fn();
    render(<MobileMenu onClick={handleClick} side="right" />);
    
    expect(screen.getByLabelText('Open workflows')).toBeInTheDocument();
  });

  it('defaults to left side', () => {
    const handleClick = jest.fn();
    render(<MobileMenu onClick={handleClick} />);
    
    expect(screen.getByLabelText('Open sidebar')).toBeInTheDocument();
  });

  it('renders hamburger icon for left side', () => {
    const handleClick = jest.fn();
    const { container } = render(<MobileMenu onClick={handleClick} side="left" />);
    
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('renders dots icon for right side', () => {
    const handleClick = jest.fn();
    const { container } = render(<MobileMenu onClick={handleClick} side="right" />);
    
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('has lg:hidden class for mobile only', () => {
    const handleClick = jest.fn();
    const { container } = render(<MobileMenu onClick={handleClick} />);
    
    const button = container.querySelector('button');
    expect(button?.className).toContain('lg:hidden');
  });
});
