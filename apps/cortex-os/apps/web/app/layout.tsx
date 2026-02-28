import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

import { Web3Provider } from "@/components/providers/Web3Provider";
import { Toaster } from "sonner";

export const metadata: Metadata = {
  title: "Cortex.OS",
  description: "DeGen Risk Auditor - Verifiable Hybrid Intelligence Swarm",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark bg-black selection:bg-emerald-500/30">
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} antialiased`}
      >
        <Web3Provider>
          {children}
        </Web3Provider>
        <Toaster richColors position="bottom-right" theme="dark" />
      </body>
    </html>
  );
}
