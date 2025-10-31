import { render, screen } from '@testing-library/react';
import { Image } from '@/components/ui/image';

describe('Image Component', () => {
  it('renders image with base64 data', () => {
    const base64Data = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
    
    render(
      <Image 
        base64={base64Data} 
        mediaType="image/png" 
        alt="Test image" 
      />
    );
    
    const img = screen.getByRole('img');
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute('alt', 'Test image');
  });

  it('renders image with correct data URL format', () => {
    const base64Data = 'abc123';
    
    render(
      <Image 
        base64={base64Data} 
        mediaType="image/jpeg" 
        alt="JPEG image" 
      />
    );
    
    const img = screen.getByRole('img') as HTMLImageElement;
    expect(img.src).toContain('data:image/jpeg;base64,abc123');
  });

  it('uses default mediaType when not provided', () => {
    const base64Data = 'xyz789';
    
    render(
      <Image 
        base64={base64Data} 
        alt="Default type image" 
      />
    );
    
    const img = screen.getByRole('img') as HTMLImageElement;
    expect(img.src).toContain('data:image/png;base64,xyz789');
  });

  it('renders placeholder when no src is available', () => {
    const { container } = render(
      <Image alt="Placeholder" />
    );
    
    // Should render a div placeholder, not an img
    const placeholder = container.querySelector('div[role="img"]');
    expect(placeholder).toBeInTheDocument();
    expect(placeholder).toHaveAttribute('aria-label', 'Placeholder');
  });

  it('applies custom className', () => {
    const base64Data = 'custom123';
    
    render(
      <Image 
        base64={base64Data} 
        alt="Custom styled" 
        className="custom-class"
      />
    );
    
    const img = screen.getByRole('img');
    expect(img).toHaveClass('custom-class');
  });

  it('renders with rounded corners by default', () => {
    const base64Data = 'rounded123';
    
    render(
      <Image 
        base64={base64Data} 
        alt="Rounded image" 
      />
    );
    
    const img = screen.getByRole('img');
    expect(img).toHaveClass('rounded-md');
  });

  it('handles Uint8Array data', async () => {
    // Create a simple Uint8Array (1x1 transparent PNG)
    const uint8Array = new Uint8Array([
      137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 13, 73, 72, 68, 82,
      0, 0, 0, 1, 0, 0, 0, 1, 8, 6, 0, 0, 0, 31, 21, 196, 137
    ]);
    
    render(
      <Image 
        uint8Array={uint8Array} 
        mediaType="image/png" 
        alt="Uint8Array image" 
      />
    );
    
    // Image should be rendered (even though blob URL is created asynchronously)
    const imgOrPlaceholder = screen.getByRole('img');
    expect(imgOrPlaceholder).toBeInTheDocument();
  });

  it('requires alt text for accessibility', () => {
    const base64Data = 'accessible123';
    
    render(
      <Image 
        base64={base64Data} 
        alt="Accessible image description" 
      />
    );
    
    const img = screen.getByRole('img');
    expect(img).toHaveAttribute('alt', 'Accessible image description');
  });

  it('has responsive sizing classes', () => {
    const base64Data = 'responsive123';
    
    render(
      <Image 
        base64={base64Data} 
        alt="Responsive image" 
      />
    );
    
    const img = screen.getByRole('img');
    expect(img).toHaveClass('h-auto');
    expect(img).toHaveClass('max-w-full');
  });
});
