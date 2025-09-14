import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Cortensor API Server',
  description: 'API server for Cortensor applications',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}