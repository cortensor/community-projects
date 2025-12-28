import { useEffect, useRef } from 'react';
import { useAccount, useSwitchChain, useChainId } from 'wagmi';
import { switchToLocalhostNetwork } from '@/utils/addLocalhostNetwork';
import { toast } from 'sonner';

const TARGET_CHAIN_ID = 31337; // Localhost 8545

/**
 * Component that automatically switches to the correct network when wallet connects
 */
export const NetworkSwitcher = () => {
  const { isConnected, connector } = useAccount();
  const chainId = useChainId();
  const { switchChain } = useSwitchChain();
  const hasSwitchedRef = useRef(false);

  useEffect(() => {
    // Reset the ref when disconnected
    if (!isConnected) {
      hasSwitchedRef.current = false;
      return;
    }

    const handleNetworkSwitch = async () => {
      // Only proceed if wallet is connected
      if (!isConnected) {
        return;
      }

      // Check if we're on the correct network
      if (chainId === TARGET_CHAIN_ID) {
        hasSwitchedRef.current = false; // Reset if already on correct network
        return; // Already on correct network
      }

      // Prevent multiple switch attempts
      if (hasSwitchedRef.current) {
        return;
      }

      hasSwitchedRef.current = true;

      // If using MetaMask, use the direct method
      if (connector?.id === 'metaMask' || connector?.id === 'metaMaskSDK' || window.ethereum?.isMetaMask) {
        try {
          console.log('Switching to Localhost 8545 network...');
          const switched = await switchToLocalhostNetwork();
          if (switched) {
            console.log('Successfully switched to Localhost 8545');
            toast.success('Switched to Localhost 8545 network');
            // Reset after successful switch
            setTimeout(() => {
              hasSwitchedRef.current = false;
            }, 2000);
          } else {
            hasSwitchedRef.current = false;
          }
        } catch (error: any) {
          console.error('Failed to switch network:', error);
          hasSwitchedRef.current = false;
          // Don't show error toast if user rejected
          if (error?.code !== 4001 && error?.code !== 'ACTION_REJECTED') {
            toast.error('Failed to switch network. Please switch to Localhost 8545 manually in MetaMask.');
          }
        }
      } else {
        // For other connectors, use wagmi's switchChain
        try {
          await switchChain({ chainId: TARGET_CHAIN_ID });
          toast.success('Switched to Localhost 8545 network');
          setTimeout(() => {
            hasSwitchedRef.current = false;
          }, 2000);
        } catch (error: any) {
          console.error('Failed to switch network:', error);
          hasSwitchedRef.current = false;
          // If network doesn't exist, try adding it
          if (error?.code === 4902 || error?.cause?.code === 4902) {
            try {
              const added = await switchToLocalhostNetwork();
              if (added) {
                toast.success('Added and switched to Localhost 8545 network');
                setTimeout(() => {
                  hasSwitchedRef.current = false;
                }, 2000);
              } else {
                hasSwitchedRef.current = false;
              }
            } catch (addError: any) {
              console.error('Failed to add network:', addError);
              hasSwitchedRef.current = false;
              if (addError?.code !== 4001 && addError?.code !== 'ACTION_REJECTED') {
                toast.error('Please add Localhost 8545 network manually in your wallet');
              }
            }
          } else if (error?.code !== 4001 && error?.code !== 'ACTION_REJECTED') {
            toast.error('Failed to switch network. Please switch manually.');
          }
        }
      }
    };

    // Small delay to ensure connection is fully established
    const timeoutId = setTimeout(() => {
      handleNetworkSwitch();
    }, 800);

    return () => clearTimeout(timeoutId);
  }, [isConnected, chainId, connector, switchChain]);

  return null; // This component doesn't render anything
};

