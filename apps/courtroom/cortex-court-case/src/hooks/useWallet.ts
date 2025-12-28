import { useState, useEffect } from 'react';
import { useAccount, useBalance, useDisconnect } from 'wagmi';
import { useConnectModal } from '@rainbow-me/rainbowkit';
import { toast } from 'sonner';

const MOCK_ADDRESS = '0x71bE63f3384f5fb98995898A86B02Fb2426c5788';
const MOCK_STORAGE_KEY = 'mock_wallet_connected';

export const useWallet = () => {
  const { address: realAddress, isConnected: realIsConnected, isConnecting, chain } = useAccount();
  const { disconnect: realDisconnect } = useDisconnect();
  const { openConnectModal } = useConnectModal();
  
  // Mock connection state
  const [mockConnected, setMockConnected] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(MOCK_STORAGE_KEY) === 'true';
    }
    return false;
  });

  // Use mock address if mock is connected, otherwise use real
  const address = mockConnected ? MOCK_ADDRESS : realAddress;
  const isConnected = mockConnected || realIsConnected;

  const { data: balance } = useBalance({
    address: address,
    enabled: !!address,
  });

  const formatAddress = (addr: string) => {
    if (!addr) return '';
    return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
  };

  const copyAddress = async () => {
    if (address) {
      await navigator.clipboard.writeText(address);
      return true;
    }
    return false;
  };

  const disconnect = () => {
    if (mockConnected) {
      setMockConnected(false);
      localStorage.removeItem(MOCK_STORAGE_KEY);
    } else {
      realDisconnect();
    }
  };

  // Custom openConnectModal that simulates connection
  const handleConnect = () => {
    // Show loading state briefly, then connect
    toast.loading('Connecting wallet...', { id: 'wallet-connect' });
    
    setTimeout(() => {
      setMockConnected(true);
      localStorage.setItem(MOCK_STORAGE_KEY, 'true');
      toast.success('Wallet connected successfully!', { id: 'wallet-connect' });
    }, 800);
  };

  return {
    address,
    isConnected,
    isConnecting: mockConnected ? false : isConnecting,
    chain: chain || { id: 31337, name: 'Localhost 8545' },
    balance,
    disconnect,
    openConnectModal: handleConnect,
    formatAddress: address ? formatAddress(address) : '',
    copyAddress,
  };
};