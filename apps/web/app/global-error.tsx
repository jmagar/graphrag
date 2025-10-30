'use client'

// This is the global error boundary - it must NOT import any components that use React context
// It will be pre-rendered by Next.js

export default function GlobalError() {
  // Simplified error page with no interactivity during pre-render
  if (typeof window === 'undefined') {
    return (
      <html suppressHydrationWarning>
        <body>
          <div style={{ padding: '2rem', textAlign: 'center' }}>
            <h1>Application Error</h1>
            <p>Please refresh the page</p>
          </div>
        </body>
      </html>
    )
  }

  // Client-side only rendering
  return (
    <html suppressHydrationWarning>
      <body suppressHydrationWarning>
        <div style={{
          display: 'flex',
          minHeight: '100vh',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#fafafa',
        }}>
          <div style={{ textAlign: 'center' }}>
            <h1 style={{ fontSize: '3.75rem', fontWeight: 'bold', color: '#18181b' }}>Error</h1>
            <p style={{ marginTop: '1rem', fontSize: '1.25rem', color: '#71717a' }}>
              Something went wrong
            </p>
            <button
              onClick={() => window.location.reload()}
              style={{
                marginTop: '1.5rem',
                display: 'inline-block',
                borderRadius: '0.5rem',
                backgroundColor: '#2563eb',
                padding: '0.75rem 1.5rem',
                color: 'white',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              Reload Page
            </button>
          </div>
        </div>
      </body>
    </html>
  )
}
