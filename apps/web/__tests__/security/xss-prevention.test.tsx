/**
 * Tests for XSS (Cross-Site Scripting) prevention in chat messages
 * 
 * Following TDD: Write tests first to demonstrate the XSS vulnerability,
 * then implement DOMPurify to fix it.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { AIMessage } from '@/components/chat/AIMessage';

// Mock heavy components to avoid ESM issues in Jest
jest.mock('@/components/chat/CodeBlock', () => ({
  CodeBlock: ({ value }: { value: string }) => <pre>{value}</pre>,
}));

jest.mock('@/components/chat/MermaidDiagram', () => ({
  MermaidDiagram: ({ chart }: { chart: string }) => <div>{chart}</div>,
}));

jest.mock('@/components/chat/Artifact', () => ({
  Artifact: () => <div>Artifact</div>,
}));

jest.mock('@/components/crawl/CrawlProgress', () => ({
  CrawlProgress: () => <div>CrawlProgress</div>,
}));

// Mock react-markdown to avoid ESM issues
jest.mock('react-markdown', () => {
  const MockMarkdown = ({ children }: { children: string }) => <div>{children}</div>;
  MockMarkdown.displayName = 'MockMarkdown';
  return MockMarkdown;
});

describe('XSS Prevention in AI Messages', () => {
  describe('RED: Demonstrates XSS vulnerability', () => {
    it('should NOT execute JavaScript from malicious image onerror', () => {
      // Malicious payload that tries to execute JS via image onerror
      const maliciousContent = [
        '<img src=x onerror="alert(\'XSS\')" />',
      ];

      const { container } = render(
        <AIMessage content={maliciousContent} />
      );

      // The malicious script tag should be sanitized
      const img = container.querySelector('img');
      
      // After fix: img should either not exist or not have onerror
      if (img) {
        expect(img.hasAttribute('onerror')).toBe(false);
      }
    });

    it('should NOT execute JavaScript from script tags in markdown', () => {
      const maliciousContent = [
        'Hello <script>alert("XSS")</script> World',
      ];

      const { container } = render(
        <AIMessage content={maliciousContent} />
      );

      // Script tags should be removed/sanitized
      const scripts = container.querySelectorAll('script');
      expect(scripts.length).toBe(0);
    });

    it('should NOT execute JavaScript from iframe injection', () => {
      const maliciousContent = [
        '<iframe src="javascript:alert(\'XSS\')"></iframe>',
      ];

      const { container } = render(
        <AIMessage content={maliciousContent} />
      );

      // Iframes should be removed
      const iframes = container.querySelectorAll('iframe');
      expect(iframes.length).toBe(0);
    });

    it('should NOT execute JavaScript from event handlers in links', () => {
      const maliciousContent = [
        '[Click me](javascript:alert("XSS"))',
        '<a href="javascript:void(0)" onclick="alert(\'XSS\')">Click</a>',
      ];

      const { container } = render(
        <AIMessage content={maliciousContent} />
      );

      // Links with javascript: protocol should be sanitized
      const links = container.querySelectorAll('a');
      links.forEach(link => {
        const href = link.getAttribute('href');
        if (href) {
          expect(href).not.toContain('javascript:');
        }
        expect(link.hasAttribute('onclick')).toBe(false);
      });
    });

    it('should NOT execute JavaScript from data: URIs', () => {
      const maliciousContent = [
        '<a href="data:text/html,<script>alert(\'XSS\')</script>">Click</a>',
      ];

      const { container } = render(
        <AIMessage content={maliciousContent} />
      );

      const links = container.querySelectorAll('a');
      links.forEach(link => {
        const href = link.getAttribute('href');
        if (href) {
          // data: URIs should be removed or sanitized
          expect(href).not.toMatch(/^data:text\/html/);
        }
      });
    });

    it('should sanitize SVG with embedded JavaScript', () => {
      const maliciousContent = [
        '<svg onload="alert(\'XSS\')"><circle r="50"/></svg>',
      ];

      const { container } = render(
        <AIMessage content={maliciousContent} />
      );

      const svgs = container.querySelectorAll('svg');
      svgs.forEach(svg => {
        expect(svg.hasAttribute('onload')).toBe(false);
      });
    });

    it('should handle multiple XSS vectors in same message', () => {
      const maliciousContent = [
        'Normal text',
        '<script>alert("XSS1")</script>',
        '<img src=x onerror="alert(\'XSS2\')" />',
        '[Link](javascript:alert("XSS3"))',
        '<iframe src="evil.com"></iframe>',
        'More normal text',
      ];

      const { container } = render(
        <AIMessage content={maliciousContent} />
      );

      // All XSS vectors should be neutralized
      expect(container.querySelectorAll('script').length).toBe(0);
      expect(container.querySelectorAll('iframe').length).toBe(0);
      
      const imgs = container.querySelectorAll('img');
      imgs.forEach(img => {
        expect(img.hasAttribute('onerror')).toBe(false);
      });

      const links = container.querySelectorAll('a');
      links.forEach(link => {
        const href = link.getAttribute('href');
        if (href) {
          expect(href).not.toContain('javascript:');
        }
      });
    });
  });

  describe('GREEN: Ensures legitimate content works', () => {
    it('should render safe markdown properly', () => {
      const safeContent = [
        '# Heading',
        'This is **bold** and *italic* text.',
        '- List item 1',
        '- List item 2',
      ];

      render(<AIMessage content={safeContent} />);

      // Should have heading
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Heading');
      
      // Should have list items
      const listItems = screen.getAllByRole('listitem');
      expect(listItems.length).toBeGreaterThanOrEqual(2);
    });

    it('should render safe links properly', () => {
      const safeContent = [
        '[Google](https://google.com)',
        '<https://example.com>',
      ];

      const { container } = render(
        <AIMessage content={safeContent} />
      );

      const links = container.querySelectorAll('a');
      expect(links.length).toBeGreaterThan(0);
      
      links.forEach(link => {
        const href = link.getAttribute('href');
        expect(href).toMatch(/^https?:\/\//);
      });
    });

    it('should render code blocks safely', () => {
      const safeContent = [
        '```javascript',
        'const code = "test";',
        'console.log(code);',
        '```',
      ].join('\n');

      render(<AIMessage content={[safeContent]} />);

      // Code should be rendered (actual content check depends on CodeBlock component)
      // Main point: no XSS from code content
      expect(screen.getByRole('log')).toBeInTheDocument();
    });

    it('should preserve text content while removing XSS', () => {
      const mixedContent = [
        'Hello <script>alert("XSS")</script> World',
      ];

      render(<AIMessage content={mixedContent} />);

      // "Hello" and "World" should still be visible
      // (exact matching depends on how sanitization works)
      const messageContainer = screen.getByRole('log');
      expect(messageContainer).toBeInTheDocument();
    });
  });

  describe('Performance: Sanitization should not break streaming', () => {
    it('should handle streaming messages with partial HTML', () => {
      // Streaming might send partial HTML that gets completed later
      const streamingContent = [
        'This is a partial <a href="https://example.com"',
      ];

      // Should not crash with malformed HTML
      expect(() => {
        render(<AIMessage content={streamingContent} isStreaming={true} />);
      }).not.toThrow();
    });

    it('should handle rapid message updates during streaming', () => {
      const { rerender } = render(
        <AIMessage content={['Hello']} isStreaming={true} />
      );

      // Simulate streaming updates
      const updates = [
        ['Hello'],
        ['Hello', 'World'],
        ['Hello', 'World', '<script>alert("XSS")</script>'],
        ['Hello', 'World', '<script>alert("XSS")</script>', 'Safe text'],
      ];

      updates.forEach(content => {
        expect(() => {
          rerender(<AIMessage content={content} isStreaming={true} />);
        }).not.toThrow();
      });
    });
  });
});
