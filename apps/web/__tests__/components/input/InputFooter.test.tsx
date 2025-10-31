import { render, screen } from '@testing-library/react';
import { InputFooter } from '@/components/input/InputFooter';

describe('InputFooter', () => {
  describe('when not focused', () => {
    beforeEach(() => {
      render(<InputFooter isFocused={false} />);
    });

    it('shows focus hint', () => {
      expect(screen.getByText(/to focus/i)).toBeInTheDocument();
    });

    it('shows ⌘+K keyboard shortcut', () => {
      expect(screen.getByText('⌘')).toBeInTheDocument();
      expect(screen.getByText('K')).toBeInTheDocument();
    });
  });

  describe('when focused', () => {
    beforeEach(() => {
      render(<InputFooter isFocused={true} />);
    });

    it('shows mention and command hints', () => {
      expect(screen.getByText(/to mention sources/i)).toBeInTheDocument();
      expect(screen.getByText(/for commands/i)).toBeInTheDocument();
    });

    it('shows @ symbol for mentions', () => {
      expect(screen.getByText('@')).toBeInTheDocument();
    });

    it('shows / symbol for commands', () => {
      expect(screen.getByText('/')).toBeInTheDocument();
    });

    it('shows ⌘+Enter keyboard shortcut', () => {
      expect(screen.getByText('⌘')).toBeInTheDocument();
      expect(screen.getByText('Enter')).toBeInTheDocument();
    });
  });
});
