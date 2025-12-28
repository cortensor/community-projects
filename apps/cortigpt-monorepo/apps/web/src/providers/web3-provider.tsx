'use client'

import { darkTheme, RainbowKitProvider } from '@rainbow-me/rainbowkit'
import { WagmiProvider } from 'wagmi'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { useState } from 'react'
import { config } from '@/lib/wagmiConfig'
import ReactQueryProvider from './react-query-provider'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Toaster } from '@/components/ui/sonner'

export function Web3Provider({ children }: Readonly<{ children: React.ReactNode }>) {


  return (
    <WagmiProvider config={config}>
      <ReactQueryProvider>
      <TooltipProvider>

        <RainbowKitProvider
          theme={darkTheme({
            accentColor: 'hsl(var(--accent))',
            accentColorForeground: 'hsl(var(--accent-foreground))',
            borderRadius: 'small',
            fontStack: 'system',
            overlayBlur: 'small',
          })}
        >

            {children}
            <Toaster
              position="top-right"
              richColors
              closeButton
              theme="dark"
            />

          {/* <ReactQueryDevtools initialIsOpen={false} /> */}
        </RainbowKitProvider>
        </TooltipProvider>

      </ReactQueryProvider>
    </WagmiProvider>
  )
}