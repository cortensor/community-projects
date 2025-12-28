import { getDefaultConfig } from '@rainbow-me/rainbowkit';
import { mainnet, sepolia, polygon, arbitrum, optimism } from 'wagmi/chains';
import { defineChain } from 'viem';

// Localhost Hardhat network - Enhanced configuration
const localhost = defineChain({
  id: 31337,
  name: 'Localhost 8545',
  nativeCurrency: {
    decimals: 18,
    name: 'Ether',
    symbol: 'ETH',
  },
  rpcUrls: {
    default: {
      http: ['http://127.0.0.1:8545'],
      webSocket: ['ws://127.0.0.1:8545'],
    },
    public: {
      http: ['http://127.0.0.1:8545'],
    },
  },
  blockExplorers: {
    default: {
      name: 'Localhost Explorer',
      url: 'http://localhost:8545',
    },
  },
  testnet: true,
});

export const config = getDefaultConfig({
  appName: 'Cortensor Judge',
  projectId: 'cortensor-judge-demo', // For demo purposes - in production use a real WalletConnect project ID
  chains: [localhost, mainnet, sepolia, polygon, arbitrum, optimism],
  ssr: false,
});

export const supportedChains = [
  { id: 31337, name: 'Localhost 8545', symbol: 'ETH' },
  { id: 1, name: 'Ethereum', symbol: 'ETH' },
  { id: 11155111, name: 'Sepolia', symbol: 'ETH' },
  { id: 137, name: 'Polygon', symbol: 'MATIC' },
  { id: 42161, name: 'Arbitrum', symbol: 'ETH' },
  { id: 10, name: 'Optimism', symbol: 'ETH' },
];