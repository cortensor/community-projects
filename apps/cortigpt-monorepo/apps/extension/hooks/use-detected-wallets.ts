import { useState, useEffect } from 'react';

interface WalletInfo {
  uuid: string;
  name: string;
  icon: string;
  rdns: string;
}

interface WalletListUpdatedMessage {
  type: 'WALLET_LIST_UPDATED';
  wallets: WalletInfo[];
}

export function useDetectedWallets() {
  const [wallets, setWallets] = useState<WalletInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Function to fetch current wallets from background
    const fetchWallets = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const response = await browser.runtime.sendMessage({
          type: 'GET_DETECTED_WALLETS'
        });

        if (response && response.wallets) {
          setWallets(response.wallets);
        }
      } catch (err) {
        console.error('Failed to fetch wallets:', err);
        setError('Failed to fetch wallets');
      } finally {
        setIsLoading(false);
      }
    };

    // Listen for wallet updates from background
    const handleMessage = (message: WalletListUpdatedMessage) => {
      if (message.type === 'WALLET_LIST_UPDATED') {
        console.log('Received wallet update:', message.wallets);
        setWallets(message.wallets);
        setError(null);
      }
    };

    // Add message listener
    browser.runtime.onMessage.addListener(handleMessage);

    // Fetch initial wallets
    fetchWallets();

    // Cleanup
    return () => {
      browser.runtime.onMessage.removeListener(handleMessage);
    };
  }, []);

  // Function to manually refresh wallets
  const refreshWallets = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await browser.runtime.sendMessage({
        type: 'GET_DETECTED_WALLETS'
      });

      if (response && response.wallets) {
        setWallets(response.wallets);
      }
    } catch (err) {
      console.error('Failed to refresh wallets:', err);
      setError('Failed to refresh wallets');
    } finally {
      setIsLoading(false);
    }
  };

  return {
    wallets,
    isLoading,
    error,
    refreshWallets,
    hasWallets: wallets.length > 0
  };
}

export type { WalletInfo };