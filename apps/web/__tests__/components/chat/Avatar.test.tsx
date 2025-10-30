import { render } from '@testing-library/react';
import { Avatar } from '@/components/chat/Avatar';

describe('Avatar', () => {
  describe('AI Avatar', () => {
    it('renders AI avatar', () => {
      const { container } = render(<Avatar type="ai" />);
      
      // Should render the avatar container
      const avatar = container.querySelector('.w-8.h-8');
      expect(avatar).toBeInTheDocument();
    });

    it('renders Mandalorian helmet elements', () => {
      const { container } = render(<Avatar type="ai" />);
      
      // Check for multiple helmet elements (visor, details)
      const helmetParts = container.querySelectorAll('div[class*="bg-zinc"]');
      expect(helmetParts.length).toBeGreaterThan(0);
    });

    it('has gradient background', () => {
      const { container } = render(<Avatar type="ai" />);
      
      const gradient = container.querySelector('.bg-gradient-to-br');
      expect(gradient).toBeInTheDocument();
    });
  });

  describe('User Avatar', () => {
    it('renders user avatar', () => {
      const { container } = render(<Avatar type="user" />);
      
      const avatar = container.querySelector('.w-8.h-8');
      expect(avatar).toBeInTheDocument();
    });

    it('renders Grogu (Baby Yoda) elements', () => {
      const { container } = render(<Avatar type="user" />);
      
      // Check for head and ears
      const groguParts = container.querySelectorAll('div[class*="bg-emerald"]');
      expect(groguParts.length).toBeGreaterThan(0);
    });

    it('has emerald gradient background', () => {
      const { container } = render(<Avatar type="user" />);
      
      const gradient = container.querySelector('.from-emerald-600');
      expect(gradient).toBeInTheDocument();
    });
  });

  describe('Custom className', () => {
    it('applies custom className to AI avatar', () => {
      const { container } = render(<Avatar type="ai" className="custom-class" />);
      
      const avatar = container.querySelector('.custom-class');
      expect(avatar).toBeInTheDocument();
    });

    it('applies custom className to user avatar', () => {
      const { container } = render(<Avatar type="user" className="custom-class" />);
      
      const avatar = container.querySelector('.custom-class');
      expect(avatar).toBeInTheDocument();
    });
  });

  describe('Different types', () => {
    it('renders differently for AI vs user', () => {
      const { container: aiContainer } = render(<Avatar type="ai" />);
      const { container: userContainer } = render(<Avatar type="user" />);
      
      // AI has zinc colors, user has emerald colors
      expect(aiContainer.querySelector('.from-zinc-700')).toBeInTheDocument();
      expect(userContainer.querySelector('.from-emerald-600')).toBeInTheDocument();
    });
  });
});
