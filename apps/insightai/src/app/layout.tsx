import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "InsightAI - AI Research Agent powered by Cortensor",
  description: "Decentralized AI research assistant using Cortensor's distributed inference network for trusted, verifiable research insights.",
  keywords: ["AI", "Research", "Cortensor", "Decentralized", "Web3"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} antialiased min-h-screen`}>
        {children}
      </body>
    </html>
  );
}
