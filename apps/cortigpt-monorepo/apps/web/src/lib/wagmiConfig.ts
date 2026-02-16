import { getDefaultConfig } from '@rainbow-me/rainbowkit'
import { arbitrumSepolia } from 'wagmi/chains'
import { http } from 'wagmi'
 

if (!process.env.NEXT_PUBLIC_ARBITRUM_SEPOLIA_RPC_URL || !process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID) {
  throw new Error('Missing environment variables')
}

export const config = getDefaultConfig({
  appName: 'CortiGPT - Verifiable Multi-Agent AI for Web3',
  projectId: process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID,
  chains: [arbitrumSepolia],
  transports: {
    [arbitrumSepolia.id]: http(process.env.NEXT_PUBLIC_ARBITRUM_SEPOLIA_RPC_URL),
  },
  ssr: true, // Enable server-side rendering support
})