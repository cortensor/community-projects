/**
 * Utility to add Localhost network to MetaMask
 * Call this function to automatically add the network
 */

export async function addLocalhostNetwork(): Promise<boolean> {
  if (!window.ethereum) {
    console.error('MetaMask is not installed');
    return false;
  }

  try {
    await window.ethereum.request({
      method: 'wallet_addEthereumChain',
      params: [
        {
          chainId: '0x7A69', // 31337 in hexadecimal
          chainName: 'Localhost 8545',
          nativeCurrency: {
            name: 'Ether',
            symbol: 'ETH',
            decimals: 18,
          },
          rpcUrls: ['http://127.0.0.1:8545'],
          blockExplorerUrls: null,
        },
      ],
    });
    console.log('Localhost network added to MetaMask');
    return true;
  } catch (error: any) {
    console.error('Error adding network:', error);
    // If network already exists, that's okay
    if (error.code === 4902) {
      console.log('Network already exists');
      return true;
    }
    return false;
  }
}

/**
 * Switch to localhost network
 */
export async function switchToLocalhostNetwork(): Promise<boolean> {
  if (!window.ethereum) {
    console.error('MetaMask is not installed');
    return false;
  }

  try {
    await window.ethereum.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId: '0x7A69' }], // 31337 in hex
    });
    return true;
  } catch (error: any) {
    // If network doesn't exist, add it
    if (error.code === 4902) {
      return await addLocalhostNetwork();
    }
    console.error('Error switching network:', error);
    return false;
  }
}

// Extend Window interface for TypeScript
declare global {
  interface Window {
    ethereum?: {
      request: (args: { method: string; params?: any[] }) => Promise<any>;
      isMetaMask?: boolean;
    };
  }
}


