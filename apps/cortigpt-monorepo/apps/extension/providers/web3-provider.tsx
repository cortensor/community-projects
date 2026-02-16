'use client'

import { darkTheme, RainbowKitProvider } from '@rainbow-me/rainbowkit'
import { WagmiProvider } from 'wagmi'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { useState } from 'react'
import ReactQueryProvider from './react-query-provider'
import { config } from '@/lib/wagmiConfig'

export  function Web3Provider({ children }: Readonly<{ children: React.ReactNode }>) {


  return (
    <WagmiProvider config={config}>
      <ReactQueryProvider>
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
          {/* <ReactQueryDevtools initialIsOpen={false} /> */}
        </RainbowKitProvider>
      </ReactQueryProvider>
    </WagmiProvider>
  )
}