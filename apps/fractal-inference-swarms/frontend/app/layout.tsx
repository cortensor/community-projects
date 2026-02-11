import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Fractal Inference Swarms | AI Orchestration Dashboard',
  description: 'AI-native orchestration system with fractal agent swarms and x402 micropayments',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-swarm-bg grid-bg antialiased">
        {children}
      </body>
    </html>
  );
}