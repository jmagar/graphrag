import Link from 'next/link'

// Force dynamic rendering
export const dynamic = 'force-dynamic'

export default function NotFound() {
  return (
    <html lang="en">
      <body>
        <div style={{
          display: 'flex',
          minHeight: '100vh',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#fafafa',
        }}>
          <div style={{ textAlign: 'center' }}>
            <h1 style={{ fontSize: '3.75rem', fontWeight: 'bold', color: '#18181b' }}>404</h1>
            <p style={{ marginTop: '1rem', fontSize: '1.25rem', color: '#71717a' }}>Page not found</p>
            <Link
              href="/"
              style={{
                marginTop: '1.5rem',
                display: 'inline-block',
                borderRadius: '0.5rem',
                backgroundColor: '#2563eb',
                padding: '0.75rem 1.5rem',
                color: 'white',
                textDecoration: 'none',
              }}
            >
              Go back home
            </Link>
          </div>
        </div>
      </body>
    </html>
  )
}
