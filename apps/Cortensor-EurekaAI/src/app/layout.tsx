// src/app/layout.tsx
import type React from "react"
import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { ThemeProvider } from "@/components/theme-provider"
import { Toaster } from "@/components/ui/toaster"
import { ErrorBoundary } from "@/components/error-boundary"
import { EnvironmentProvider } from "@/contexts/environment-context"
import { KeyboardHandler } from "@/components/keyboard-handler"

// Impor stylesheet setelah instalasi highlight.js
import 'highlight.js/styles/github-dark.css';

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "Eureka - AI Assistant",
  description: "Intelligent AI assistant powered by Cortensor Network (Professional Edition)",
  icons: {
    icon: "/favicon.ico",
  },
  generator: 'Eureka.dev',
  keywords: ['AI', 'Assistant', 'Cortensor', 'Blockchain', 'Chat', 'Eureka', 'Artificial Intelligence', 'Professional'],
  authors: [{ name: 'Eureka Team' }],
  openGraph: {
    title: "Eureka - AI Assistant",
    description: "Intelligent AI assistant powered by Cortensor Network",
    type: 'website',
    locale: 'en_US',
  },
  twitter: {
    card: 'summary_large_image',
    title: "Eureka - AI Assistant",
    description: "Intelligent AI assistant powered by Cortensor Network",
  },
  robots: {
    index: true,
    follow: true,
  },
}

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: 'cover'
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <ErrorBoundary>
          <EnvironmentProvider>
            <KeyboardHandler>
              <ThemeProvider
                attribute="class"
                defaultTheme="dark"
                enableSystem={false}
                forcedTheme="dark"
                disableTransitionOnChange
              >
                {children}
                <Toaster />
              </ThemeProvider>
            </KeyboardHandler>
          </EnvironmentProvider>
        </ErrorBoundary>
      </body>
    </html>
  )
}
