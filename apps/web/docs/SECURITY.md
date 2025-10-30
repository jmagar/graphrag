# Security Documentation

## XSS (Cross-Site Scripting) Protection

### Built-in Protection via react-markdown

The AIMessage component uses `react-markdown` for rendering AI responses, which provides **built-in XSS protection**:

1. **HTML Sanitization**: react-markdown does NOT render raw HTML by default
   - `<script>` tags are stripped
   - Event handlers (`onclick`, `onerror`, etc.) are removed
   - `javascript:` URLs are blocked

2. **Safe Component Rendering**: All HTML elements are rendered as React components
   - Custom components control what attributes are allowed
   - Images are explicitly disabled (`img: () => null`)
   - Links are wrapped with safe attributes (`target="_blank"`, `rel="noopener noreferrer"`)

3. **Configuration**:
   ```typescript
   <ReactMarkdown
     remarkPlugins={[remarkGfm, remarkMath]}
     rehypePlugins={[rehypeKatex]}
     components={{
       img: () => null,  // No images allowed
       a: ({ href, children }) => (
         <a
           href={href}
           target="_blank"
           rel="noopener noreferrer"  // Prevents tabnabbing
         >
           {children}
         </a>
       ),
     }}
   >
     {content}
   </ReactMarkdown>
   ```

### Protection Against Common XSS Vectors

| Attack Vector | Protection |
|--------------|------------|
| `<script>alert('XSS')</script>` | ✅ Stripped by react-markdown |
| `<img src=x onerror="alert('XSS')">` | ✅ Images disabled + event handlers removed |
| `<a href="javascript:alert('XSS')">` | ✅ JavaScript URLs blocked |
| `<iframe src="evil.com">` | ✅ Iframes not rendered |
| `<svg onload="alert('XSS')">` | ✅ Event handlers removed |

### Additional Security Measures

1. **No `dangerouslySetInnerHTML`**: We never use this React prop
2. **Content Security Policy (CSP)**: Consider adding CSP headers in production
3. **Input Validation**: API validates all inputs before processing
4. **Rate Limiting**: 5 messages per minute to prevent abuse

### Testing XSS Protection

See `__tests__/security/xss-prevention.test.tsx` for comprehensive XSS tests.

### When to Use DOMPurify

DOMPurify is **not needed** for markdown content rendered via react-markdown. However, if you ever need to render raw HTML (NOT RECOMMENDED), use:

```typescript
import DOMPurify from 'isomorphic-dompurify';

const cleanHTML = DOMPurify.sanitize(dirtyHTML, {
  ALLOWED_TAGS: ['p', 'b', 'i', 'em', 'strong', 'a'],
  ALLOWED_ATTR: ['href'],
});
```

## Memory Leak Prevention

### Abort Controller Cleanup

The chat page properly cleans up in-flight requests on unmount:

```typescript
useEffect(() => {
  return () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };
}, []);
```

### Interval Cleanup

All polling intervals are cleared on unmount:

```typescript
useEffect(() => {
  const intervals = new Map<string, NodeJS.Timeout>();
  
  // ... setup polling

  return () => {
    intervals.forEach(interval => clearInterval(interval));
    intervals.clear();
  };
}, [dependencies]);
```

## User Experience

### Non-Blocking Notifications

We use **sonner** toast notifications instead of blocking `alert()`:

**❌ Bad (Blocking):**
```typescript
alert('Rate limit: Please wait.');
```

**✅ Good (Non-blocking):**
```typescript
toast.error('Rate limit exceeded', {
  description: 'You can only send 5 messages per minute. Please wait.',
  duration: 4000,
});
```

### Benefits:
- Non-blocking UI
- Accessible (aria-live regions)
- Dismissible
- Consistent styling
- Auto-dismiss with timeout

## Error Handling Best Practices

### Consistent Message Format

All assistant messages use **array format** for content:

**❌ Bad:**
```typescript
content: `Error message`  // String
```

**✅ Good:**
```typescript
content: [`Error message`]  // Array
```

This ensures type consistency and proper rendering in the AIMessage component.

### Error Logging

Always log errors with context:

```typescript
try {
  await riskyOperation();
} catch (error) {
  console.error('Operation failed:', error);
  toast.error('Operation failed', {
    description: error.message,
  });
}
```

## Security Checklist

- [x] XSS protection via react-markdown
- [x] No `dangerouslySetInnerHTML` usage
- [x] Abort controller cleanup on unmount
- [x] Interval cleanup on unmount
- [x] Non-blocking error notifications (toast)
- [x] Consistent error message format
- [x] Rate limiting (5 messages/minute)
- [ ] Content Security Policy headers (TODO: Add in production)
- [ ] HTTPS enforcement (TODO: Production deployment)

## Future Improvements

1. **Content Security Policy**: Add CSP headers to prevent inline script execution
2. **Rate Limiting Backend**: Move rate limiting to backend API
3. **Request Signing**: Sign API requests to prevent tampering
4. **Audit Logging**: Log security-relevant events for monitoring
