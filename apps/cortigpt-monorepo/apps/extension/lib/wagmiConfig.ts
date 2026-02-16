import { getDefaultConfig } from '@rainbow-me/rainbowkit'
import { arbitrumSepolia } from 'wagmi/chains'
import { http } from 'wagmi'


if (!import.meta.env.VITE_ARBITRUM_SEPOLIA_RPC_URL || !import.meta.env.VITE_WALLETCONNECT_PROJECT_ID) {
  throw new Error('Missing environment variables')
}

export const config = getDefaultConfig({
  appName: 'CortiGPT - Verifiable Multi-Agent AI for Web3',
  projectId: import.meta.env.VITE_WALLETCONNECT_PROJECT_ID,
  chains: [arbitrumSepolia],
  transports: {
    [arbitrumSepolia.id]: http(import.meta.env.VITE_ARBITRUM_SEPOLIA_RPC_URL),
  },
  ssr: false, // Disable SSR for Chrome extension
  multiInjectedProviderDiscovery: true, // Enable EIP-6963 for multi-wallet detection
})