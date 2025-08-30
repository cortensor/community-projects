import { arbitrumSepolia } from 'viem/chains';

// This check is the key to the whole pattern. 'window' only exists in the browser.
const isServer = typeof window === 'undefined';

/**
 * A helper function to throw a clear error if a required variable is missing.
 */
const assertIsSet = <T>(value: T | undefined, name: string): T => {
  if (!value) {
    throw new Error(`CRITICAL ERROR: Required variable ${name} is not set.`);
  }
  return value;
}

export const config = {
  chain: arbitrumSepolia,

  // This is public and safe to use on both client and server.
  rpc: {
    http: assertIsSet(process.env.NEXT_PUBLIC_ARBITRUM_SEPOLIA_RPC_URL, 'NEXT_PUBLIC_ARBITRUM_SEPOLIA_RPC_URL'),
  },

  // These are also public.
  contracts: {
    sessionV2: { address: assertIsSet(process.env.NEXT_PUBLIC_SESSION_V2_ADDRESS, 'NEXT_PUBLIC_SESSION_V2_ADDRESS') as `0x${string}` },
    sessionQueueV2: { address: assertIsSet(process.env.NEXT_PUBLIC_SESSION_QUEUE_V2_ADDRESS, 'NEXT_PUBLIC_SESSION_QUEUE_V2_ADDRESS') as `0x${string}` },
  },

  // This is a SERVER-ONLY secret.
  // The value will be the private key string on the server, and `undefined` on the client.
  privateKey: (isServer ? process.env.WALLET_PRIVATE_KEY : '') as `0x${string}`,
};