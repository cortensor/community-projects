// Configuration for Web3 integration
// This would contain actual configuration for Cortensor integration

export const config = {
  web3: {
    enabled: false, // Set to true when Web3 features are ready
    routerNodeUrl: process.env.NEXT_PUBLIC_ROUTER_NODE_URL || '',
    apiKey: process.env.NEXT_PUBLIC_WEB3_API_KEY || '',
    defaultNetwork: 'testnet',
    sessionV2Address: process.env.NEXT_PUBLIC_SESSION_V2_ADDRESS || '0x1234567890abcdef1234567890abcdef12345678',
    sessionQueueV2Address: process.env.NEXT_PUBLIC_SESSION_QUEUE_V2_ADDRESS || '0xabcdef1234567890abcdef1234567890abcdef12'
  },
  app: {
    name: 'Eureka',
    version: '1.0.0'
  }
}
