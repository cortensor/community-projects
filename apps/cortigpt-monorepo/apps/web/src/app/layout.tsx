import type { Metadata, Viewport } from "next";
import { Orbitron, Space_Grotesk } from "next/font/google";
import "./globals.css";
import "@rainbow-me/rainbowkit/styles.css";
import { Web3Provider } from "@/providers/web3-provider";
import Navbar from "@/components/layout/Navbar";
import { Analytics } from "@vercel/analytics/next"
const orbitron = Orbitron({
  variable: "--font-orbitron",
  subsets: ["latin"],
  weight: ["400", "700", "900"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: {
    default: "CortiGPT - The Decentralized Perplexity | Verifiable AI Search",
    template: "%s | CortiGPT"
  },
  description: "Experience the future of AI-powered search with CortiGPT - where Perplexity meets Decentralization. Get verifiable, trustless intelligence from multiple specialized AI agents on the Cortensor protocol with immutable proof receipts.",
  keywords: [
    "CortiGPT",
    "Cortensor",
    "decentralized AI",
    "verifiable AI",
    "AI search",
    "Web3 AI",
    "blockchain AI",
    "trustless AI",
    "multi-agent AI",
    "decentralized Perplexity",
    "AI miners",
    "proof receipts",
    "neural network",
    "distributed AI"
  ],
  authors: [{ name: "Cortensor Team" }],
  creator: "Cortensor",
  publisher: "Cortensor",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  metadataBase: new URL('https://cortigpt.jatique.dev'),
  alternates: {
    canonical: '/',
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://cortigpt.jatique.dev',
    title: 'CortiGPT - The Decentralized Perplexity | Verifiable AI Search',
    description: 'Experience the future of AI-powered search with CortiGPT - where Perplexity meets Decentralization. Get verifiable, trustless intelligence from multiple specialized AI agents.',
    siteName: 'CortiGPT',
    images: [
      {
        url: '/cortigpt-4.png',
        width: 1200,
        height: 630,
        alt: 'CortiGPT - Decentralized AI Search Platform',
        type: 'image/png',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'CortiGPT - The Decentralized Perplexity',
    description: 'Experience verifiable, trustless AI intelligence with immutable proof receipts. Where Perplexity meets Decentralization.',
    images: ['/cortigpt-4.png'],
    creator: '@ezejaemmanuel36',
    // site: '@cortensor',
  },
  icons: {
    icon: [
      { url: '/cortigpt-4.png', sizes: '32x32', type: 'image/png' },
      { url: '/cortigpt-4.png', sizes: '16x16', type: 'image/png' },
    ],
    apple: [
      { url: '/cortigpt-4.png', sizes: '180x180', type: 'image/png' },
    ],
    shortcut: '/cortigpt-4.png',
  },
  manifest: '/manifest.json',
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  verification: {
    google: 'your-google-verification-code',
    yandex: 'your-yandex-verification-code',
  },
  category: 'technology',
  classification: 'AI, Blockchain, Web3, Decentralized Technology',
  other: {
    'theme-color': '#0066ff',
    'color-scheme': 'dark light',
    'apple-mobile-web-app-capable': 'yes',
    'apple-mobile-web-app-status-bar-style': 'black-translucent',
    'apple-mobile-web-app-title': 'CortiGPT',
    'application-name': 'CortiGPT',
    'msapplication-TileColor': '#0066ff',
    'msapplication-config': '/browserconfig.xml',
  },
};

export const viewport: Viewport = {
  initialScale: 1,
  width: 'device-width',
  maximumScale: 1,
  viewportFit: 'cover',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${orbitron.variable} ${spaceGrotesk.variable} antialiased`}>
        <Web3Provider>
          <Navbar />
          <Analytics />
          <div className="pt-20">
            {children}
          </div>
        </Web3Provider>
      </body>
    </html>
  );
}
