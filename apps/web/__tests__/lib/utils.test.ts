import { cn } from '@/lib/utils';

describe('cn utility function', () => {
  it('merges class names', () => {
    const result = cn('foo', 'bar');
    expect(result).toBe('foo bar');
  });

  it('handles conditional classes', () => {
    const result = cn('foo', false && 'bar', 'baz');
    expect(result).toBe('foo baz');
  });

  it('handles undefined and null values', () => {
    const result = cn('foo', undefined, null, 'bar');
    expect(result).toBe('foo bar');
  });

  it('handles empty input', () => {
    const result = cn();
    expect(result).toBe('');
  });

  it('handles Tailwind merge correctly', () => {
    // clsx + twMerge should handle Tailwind conflicts
    const result = cn('px-2', 'px-4');
    // twMerge should keep only the last px-* class
    expect(result).toBe('px-4');
  });

  it('handles multiple conflicting utilities', () => {
    const result = cn('text-red-500', 'text-blue-500');
    // Should keep only the last color
    expect(result).toBe('text-blue-500');
  });

  it('preserves non-conflicting classes', () => {
    const result = cn('px-4', 'py-2', 'bg-blue-500');
    expect(result).toContain('px-4');
    expect(result).toContain('py-2');
    expect(result).toContain('bg-blue-500');
  });

  it('handles array inputs', () => {
    const result = cn(['foo', 'bar'], 'baz');
    expect(result).toContain('foo');
    expect(result).toContain('bar');
    expect(result).toContain('baz');
  });

  it('handles object inputs', () => {
    const result = cn({ foo: true, bar: false, baz: true });
    expect(result).toContain('foo');
    expect(result).not.toContain('bar');
    expect(result).toContain('baz');
  });

  it('handles responsive and pseudo-class conflicts', () => {
    const result = cn('hover:px-2', 'hover:px-4', 'md:text-sm', 'md:text-lg');
    // Should resolve Tailwind conflicts, keeping the last of each variant
    expect(result).toContain('hover:px-4');
    expect(result).toContain('md:text-lg');
    expect(result).not.toContain('hover:px-2');
    expect(result).not.toContain('md:text-sm');
  });

  it('handles deeply nested arrays and objects', () => {
    const result = cn(
      ['foo', ['bar', 'baz']],
      { nested: true, unused: false },
      [['deeply', 'nested'], 'value']
    );
    expect(result).toContain('foo');
    expect(result).toContain('bar');
    expect(result).toContain('baz');
    expect(result).toContain('nested');
    expect(result).not.toContain('unused');
    expect(result).toContain('deeply');
    expect(result).toContain('value');
  });

  it('handles empty strings and whitespace', () => {
    const result = cn('foo', '', '  ', 'bar');
    expect(result).toBe('foo bar');
  });
});
