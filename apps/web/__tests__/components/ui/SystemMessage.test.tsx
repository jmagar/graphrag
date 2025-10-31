import { render, screen, fireEvent } from '@testing-library/react';
import { SystemMessage } from '@/components/ui/system-message';

describe('SystemMessage', () => {
  it('renders message content', () => {
    render(<SystemMessage>Test message</SystemMessage>);
    
    expect(screen.getByText('Test message')).toBeInTheDocument();
  });

  it('renders with action variant by default', () => {
    const { container } = render(<SystemMessage>Action message</SystemMessage>);
    
    const messageDiv = container.firstChild as HTMLElement;
    expect(messageDiv).toHaveClass('text-zinc-700');
  });

  it('renders with error variant', () => {
    const { container } = render(
      <SystemMessage variant="error">Error message</SystemMessage>
    );
    
    const messageDiv = container.firstChild as HTMLElement;
    expect(messageDiv).toHaveClass('text-red-700');
  });

  it('renders with warning variant', () => {
    const { container } = render(
      <SystemMessage variant="warning">Warning message</SystemMessage>
    );
    
    const messageDiv = container.firstChild as HTMLElement;
    expect(messageDiv).toHaveClass('text-amber-700');
  });

  it('renders with filled background', () => {
    const { container } = render(
      <SystemMessage fill>Filled message</SystemMessage>
    );
    
    const messageDiv = container.firstChild as HTMLElement;
    expect(messageDiv).toHaveClass('bg-zinc-100');
  });

  it('renders default icon for action variant', () => {
    render(<SystemMessage variant="action">Action</SystemMessage>);
    
    // Info icon should be present
    const icon = document.querySelector('svg');
    expect(icon).toBeInTheDocument();
  });

  it('renders alert circle icon for error variant', () => {
    render(<SystemMessage variant="error">Error</SystemMessage>);
    
    const icon = document.querySelector('svg');
    expect(icon).toBeInTheDocument();
  });

  it('renders alert triangle icon for warning variant', () => {
    render(<SystemMessage variant="warning">Warning</SystemMessage>);
    
    const icon = document.querySelector('svg');
    expect(icon).toBeInTheDocument();
  });

  it('hides icon when isIconHidden is true', () => {
    render(<SystemMessage isIconHidden>No icon</SystemMessage>);
    
    const icon = document.querySelector('svg');
    expect(icon).not.toBeInTheDocument();
  });

  it('renders custom icon when provided', () => {
    render(
      <SystemMessage icon={<span data-testid="custom-icon">★</span>}>
        Custom icon message
      </SystemMessage>
    );
    
    expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
  });

  it('renders CTA button when provided', () => {
    const handleClick = jest.fn();
    
    render(
      <SystemMessage
        cta={{
          label: 'Dismiss',
          onClick: handleClick,
        }}
      >
        Message with CTA
      </SystemMessage>
    );
    
    const button = screen.getByRole('button', { name: /dismiss/i });
    expect(button).toBeInTheDocument();
  });

  it('calls CTA onClick when button is clicked', () => {
    const handleClick = jest.fn();
    
    render(
      <SystemMessage
        cta={{
          label: 'Action',
          onClick: handleClick,
        }}
      >
        Actionable message
      </SystemMessage>
    );
    
    const button = screen.getByRole('button', { name: /action/i });
    fireEvent.click(button);
    
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('does not render CTA button when not provided', () => {
    render(<SystemMessage>Message without CTA</SystemMessage>);
    
    const button = screen.queryByRole('button');
    expect(button).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <SystemMessage className="custom-class">Custom styled</SystemMessage>
    );
    
    const messageDiv = container.firstChild as HTMLElement;
    expect(messageDiv).toHaveClass('custom-class');
  });

  it('renders with error variant and filled background', () => {
    const { container } = render(
      <SystemMessage variant="error" fill>
        Critical error
      </SystemMessage>
    );
    
    const messageDiv = container.firstChild as HTMLElement;
    expect(messageDiv).toHaveClass('text-red-700');
    expect(messageDiv).toHaveClass('bg-red-100');
  });

  it('renders with warning variant and filled background', () => {
    const { container } = render(
      <SystemMessage variant="warning" fill>
        Important warning
      </SystemMessage>
    );
    
    const messageDiv = container.firstChild as HTMLElement;
    expect(messageDiv).toHaveClass('text-amber-700');
    expect(messageDiv).toHaveClass('bg-amber-100');
  });

  it('supports nested content', () => {
    render(
      <SystemMessage>
        <div>
          <strong>Bold text</strong>
          <p>Paragraph text</p>
        </div>
      </SystemMessage>
    );
    
    expect(screen.getByText('Bold text')).toBeInTheDocument();
    expect(screen.getByText('Paragraph text')).toBeInTheDocument();
  });
});
