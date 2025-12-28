import { useEffect, useRef } from 'react';
import { useAccount, useConnect, useReconnect, useDisconnect } from 'wagmi';

/**
 * Component that monitors MetaMask connection state and syncs it with wagmi
 * This helps fix the issue where MetaMask connects but the frontend doesn't detect it
 */
export const ConnectionMonitor = () => {
  const { isConnected, address, connector } = useAccount();
  const { connect, connectors } = useConnect();
  const { reconnect } = useReconnect();
  const { disconnect } = useDisconnect();
  const syncAttemptedRef = useRef(false);
  const lastCheckRef = useRef(0);
  const reconnectAttemptedRef = useRef(false);

  useEffect(() => {
    // Check if MetaMask is connected but wagmi doesn't know about it
    const checkMetaMaskConnection = async () => {
      if (!window.ethereum?.isMetaMask) {
        return;
      }

      // If already connected, reset the ref
      if (isConnected && address) {
        syncAttemptedRef.current = false;
        return;
      }

      // Throttle checks to avoid too many attempts
      const now = Date.now();
      if (now - lastCheckRef.current < 2000) {
        return;
      }
      lastCheckRef.current = now;

      // Prevent multiple sync attempts within a short time
      if (syncAttemptedRef.current) {
        return;
      }

      try {
        // Check if MetaMask has accounts connected
        const accounts = await window.ethereum.request({ 
          method: 'eth_accounts' 
        });

        console.log('ConnectionMonitor: MetaMask accounts:', accounts, 'wagmi connected:', isConnected);

        // If MetaMask has accounts but wagmi doesn't show connection
        if (accounts && accounts.length > 0 && !isConnected) {
          console.log('⚠️ MetaMask is connected but wagmi state is not synced. Attempting to sync...');
          syncAttemptedRef.current = true;
          
          // Find MetaMask connector - try multiple possible IDs
          const metaMaskConnector = connectors.find(
            (c) => 
              c.id === 'metaMask' || 
              c.id === 'metaMaskSDK' || 
              c.name?.toLowerCase().includes('metamask') ||
              c.id === 'io.metamask'
          );

          console.log('Found MetaMask connector:', metaMaskConnector?.id, metaMaskConnector?.name);

          if (metaMaskConnector) {
            try {
              console.log('Attempting to connect with MetaMask connector...');
              
              // Strategy: Disconnect completely first, then connect fresh
              // This ensures wagmi's state is reset
              if (connector) {
                console.log('Disconnecting existing connector to reset state...');
                try {
                  disconnect();
                  await new Promise(resolve => setTimeout(resolve, 500));
                  console.log('✅ Disconnected');
                } catch (disconnectError) {
                  console.log('Disconnect error (might be fine):', disconnectError);
                }
              }
              
              // Now connect fresh
              console.log('Connecting fresh with MetaMask connector...');
              try {
                const result = await connect({ 
                  connector: metaMaskConnector,
                  chainId: 31337 // Localhost 8545
                });
                console.log('✅ Connect() completed:', result);
                
                // Wait a moment for wagmi to update state
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                // Force a state refresh by triggering accountsChanged event
                // This helps wagmi detect the connection
                try {
                  const accounts = await window.ethereum?.request({ method: 'eth_accounts' });
                  if (accounts && accounts.length > 0) {
                    console.log('Triggering accountsChanged event to force state update...');
                    const ethereum = window.ethereum as any;
                    if (ethereum && typeof ethereum.emit === 'function') {
                      ethereum.emit('accountsChanged', accounts);
                    }
                    // Also try reconnect to force wagmi to re-read
                    setTimeout(async () => {
                      try {
                        await reconnect();
                        console.log('✅ Reconnect after connect completed');
                      } catch (reconnectErr) {
                        console.log('Reconnect error (might be fine):', reconnectErr);
                      }
                      // Reset refs to allow another check
                      syncAttemptedRef.current = false;
                      reconnectAttemptedRef.current = false;
                    }, 500);
                    return;
                  }
                } catch (eventError) {
                  console.error('Error triggering events:', eventError);
                }
                
                // Reset refs
                syncAttemptedRef.current = false;
                reconnectAttemptedRef.current = false;
              } catch (connectError: any) {
                console.error('❌ Connect() failed:', connectError);
                // If connect fails, try reconnect as fallback
                if (connectError?.code !== 4001 && connectError?.code !== 'ACTION_REJECTED') {
                  try {
                    console.log('Trying reconnect as fallback...');
                    await reconnect();
                    console.log('✅ Reconnect fallback successful');
                  } catch (reconnectErr) {
                    console.error('Reconnect fallback also failed:', reconnectErr);
                  }
                }
                syncAttemptedRef.current = false;
                reconnectAttemptedRef.current = false;
              }
            } catch (error: any) {
              console.error('❌ Failed to sync connection via connector:', error);
              
              // Fallback: Try direct eth_requestAccounts if connector fails
              if (error?.code !== 4001 && error?.code !== 'ACTION_REJECTED' && error?.name !== 'UserRejectedRequestError') {
                try {
                  console.log('Trying fallback: direct eth_requestAccounts...');
                  await window.ethereum.request({ method: 'eth_requestAccounts' });
                  console.log('✅ Fallback connection successful');
                  // Wait a bit and check again
                  setTimeout(() => {
                    syncAttemptedRef.current = false;
                    checkMetaMaskConnection();
                  }, 1000);
                } catch (fallbackError: any) {
                  console.error('❌ Fallback also failed:', fallbackError);
                  syncAttemptedRef.current = false;
                }
              } else {
                // User rejected, wait longer before retry
                setTimeout(() => {
                  syncAttemptedRef.current = false;
                }, 5000);
              }
            }
          } else {
            console.warn('MetaMask connector not found in available connectors:', connectors.map(c => ({ id: c.id, name: c.name })));
            // Try direct connection as fallback
            try {
              console.log('Trying direct connection without connector...');
              await window.ethereum.request({ method: 'eth_requestAccounts' });
              setTimeout(() => {
                syncAttemptedRef.current = false;
                checkMetaMaskConnection();
              }, 1000);
            } catch (error) {
              console.error('Direct connection also failed:', error);
              syncAttemptedRef.current = false;
            }
          }
        } else if (!accounts || accounts.length === 0) {
          // No accounts in MetaMask, reset
          syncAttemptedRef.current = false;
        }
      } catch (error) {
        console.error('Error checking MetaMask connection:', error);
        syncAttemptedRef.current = false;
      }
    };

    // Check immediately and then periodically
    const initialDelay = setTimeout(checkMetaMaskConnection, 1000);
    const interval = setInterval(checkMetaMaskConnection, 3000);

    // Listen to MetaMask account changes
    const handleAccountsChanged = (accounts: string[]) => {
      console.log('🔔 MetaMask accounts changed:', accounts);
      syncAttemptedRef.current = false; // Reset on account change
      if (accounts.length > 0 && !isConnected) {
        // Account is connected in MetaMask, try to sync
        setTimeout(checkMetaMaskConnection, 1000);
      }
    };

    // Listen to chain changes
    const handleChainChanged = (chainId: string) => {
      console.log('🔔 MetaMask chain changed:', chainId);
      syncAttemptedRef.current = false; // Reset on chain change
      // Refresh connection state
      setTimeout(checkMetaMaskConnection, 1000);
    };

    // Listen to connect event
    const handleConnect = () => {
      console.log('🔔 MetaMask connect event');
      syncAttemptedRef.current = false;
      setTimeout(checkMetaMaskConnection, 500);
    };

    const ethereum = window.ethereum as any;
    if (ethereum && typeof ethereum.on === 'function') {
      ethereum.on('accountsChanged', handleAccountsChanged);
      ethereum.on('chainChanged', handleChainChanged);
      ethereum.on('connect', handleConnect);
    }

    return () => {
      clearTimeout(initialDelay);
      clearInterval(interval);
      if (ethereum && typeof ethereum.removeListener === 'function') {
        ethereum.removeListener('accountsChanged', handleAccountsChanged);
        ethereum.removeListener('chainChanged', handleChainChanged);
        ethereum.removeListener('connect', handleConnect);
      }
    };
  }, [isConnected, address, connector, connect, connectors, reconnect, disconnect]);

  return null;
};

// Note: window.ethereum type is handled by wagmi/viem, we use type assertions where needed

