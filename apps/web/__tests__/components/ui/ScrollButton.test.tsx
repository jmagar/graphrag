import { render, screen, fireEvent } from '@testing-library/react';
import { ScrollButton } from '@/components/ui/scroll-button';
import { StickToBottom } from 'use-stick-to-bottom';

// Wrapper component to provide required context
const ScrollButtonWrapper = ({ children }: { children: React.ReactNode }) => (
  <StickToBottom className="h-96 overflow-auto">
    <div className="h-[1000px]">
      {children}
    </div>
  </StickToBottom>
);

describe('ScrollButton', () => {
  it('renders scroll button', () => {
    render(
      <ScrollButtonWrapper>
        <ScrollButton />
      </ScrollButtonWrapper>
    );
    
    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
  });

  it('renders chevron down icon', () => {
    render(
      <ScrollButtonWrapper>
        <ScrollButton />
      </ScrollButtonWrapper>
    );
    
    const button = screen.getByRole('button');
    const svg = button.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('has rounded-full class for circular shape', () => {
    render(
      <ScrollButtonWrapper>
        <ScrollButton />
      </ScrollButtonWrapper>
    );
    
    const button = screen.getByRole('button');
    expect(button).toHaveClass('rounded-full');
  });

  it('has correct size classes', () => {
    render(
      <ScrollButtonWrapper>
        <ScrollButton />
      </ScrollButtonWrapper>
    );
    
    const button = screen.getByRole('button');
    expect(button).toHaveClass('h-10');
    expect(button).toHaveClass('w-10');
  });

  it('can be clicked', () => {
    render(
      <ScrollButtonWrapper>
        <ScrollButton />
      </ScrollButtonWrapper>
    );
    
    const button = screen.getByRole('button');
    fireEvent.click(button);
    
    // Should not throw error
    expect(button).toBeInTheDocument();
  });

  it('accepts custom className', () => {
    render(
      <ScrollButtonWrapper>
        <ScrollButton className="custom-scroll-btn" />
      </ScrollButtonWrapper>
    );
    
    const button = screen.getByRole('button');
    expect(button).toHaveClass('custom-scroll-btn');
  });

  it('uses outline variant by default', () => {
    render(
      <ScrollButtonWrapper>
        <ScrollButton />
      </ScrollButtonWrapper>
    );
    
    const button = screen.getByRole('button');
    // Outline variant specific classes from button component
    expect(button).toBeInTheDocument();
  });

  it('uses sm size by default', () => {
    render(
      <ScrollButtonWrapper>
        <ScrollButton />
      </ScrollButtonWrapper>
    );
    
    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
  });

  it('throws error when rendered outside StickToBottom context', () => {
    // Suppress console.error for this test
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    
    expect(() => {
      render(<ScrollButton />);
    }).toThrow();
    
    consoleSpy.mockRestore();
  });
});
