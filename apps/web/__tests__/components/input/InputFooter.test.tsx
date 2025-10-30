import { render, screen } from '@testing-library/react';
import { InputFooter } from '@/components/input/InputFooter';

describe('InputFooter', () => {
  describe('when not focused', () => {
    it('shows focus hint', () => {
      render(<InputFooter isFocused={false} />);
      
      expect(screen.getByText(/to focus/i)).toBeInTheDocument();
    });

    it('shows ⌘+K keyboard shortcut', () => {
      render(<InputFooter isFocused={false} />);
      
      expect(screen.getByText('⌘')).toBeInTheDocument();
      expect(screen.getByText('K')).toBeInTheDocument();
    });
  });

  describe('when focused', () => {
    it('shows mention and command hints', () => {
      render(<InputFooter isFocused={true} />);
      
      expect(screen.getByText(/to mention sources/i)).toBeInTheDocument();
      expect(screen.getByText(/for commands/i)).toBeInTheDocument();
    });

    it('shows @ symbol for mentions', () => {
      render(<InputFooter isFocused={true} />);
      
      expect(screen.getByText('@')).toBeInTheDocument();
    });

    it('shows / symbol for commands', () => {
      render(<InputFooter isFocused={true} />);
      
      expect(screen.getByText('/')).toBeInTheDocument();
    });

    it('shows ⌘+Enter keyboard shortcut', () => {
      render(<InputFooter isFocused={true} />);
      
      expect(screen.getByText('⌘')).toBeInTheDocument();
      expect(screen.getByText('Enter')).toBeInTheDocument();
    });
  });
});
