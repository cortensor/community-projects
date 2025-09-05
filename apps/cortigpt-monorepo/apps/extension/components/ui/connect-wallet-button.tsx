"use client";
import { Button } from "@/components/ui/button";
import { ConnectButton } from '@rainbow-me/rainbowkit';

interface ConnectWalletButtonProps {
  onModalOpen?: () => void;
  className?: string;
  isMobile?: boolean;
}

export const ConnectWalletButton = ({ onModalOpen, className = "", isMobile = false }: ConnectWalletButtonProps) => {
  return (
    <div className={`${className}`}>
      <ConnectButton.Custom>
        {({
          account,
          chain,
          openAccountModal,
          openChainModal,
          openConnectModal,
          authenticationStatus,
          mounted,
        }) => {
          const ready = mounted && authenticationStatus !== 'loading';
          const connected =
            ready &&
            account &&
            chain &&
            (!authenticationStatus ||
              authenticationStatus === 'authenticated');

          return (
            <div
              {...(!ready && {
                'aria-hidden': true,
                'style': {
                  opacity: 0,
                  pointerEvents: 'none',
                  userSelect: 'none',
                },
              })}
            >
              {(() => {
                if (!connected) {
                  return (
                    <Button 
                      onClick={() => {
                        openConnectModal();
                        onModalOpen?.();
                      }} 
                      size={isMobile ? "sm" : "default"}
                      className={`${
                        isMobile 
                          ? 'w-full px-3 py-2 text-sm' 
                          : 'px-4 py-2'
                      } bg-gradient-primary hover:opacity-90 glow-primary transition-all duration-200 font-medium`}
                    >
                      Connect Wallet
                    </Button>
                  );
                }

                if (chain.unsupported) {
                  return (
                    <Button 
                      onClick={() => {
                        openChainModal();
                        onModalOpen?.();
                      }} 
                      variant="destructive"
                      size={isMobile ? "sm" : "default"}
                      className={`${
                        isMobile 
                          ? 'w-full px-3 py-2 text-sm' 
                          : 'px-4 py-2'
                      } animate-pulse`}
                    >
                      Wrong network
                    </Button>
                  );
                }

                return (
                  <div className={`flex items-center ${
                    isMobile ? 'space-x-1' : 'space-x-2'
                  }`}>
                    <Button
                      onClick={() => {
                        openChainModal();
                        onModalOpen?.();
                      }}
                      variant="outline"
                      size="sm"
                      className={`${
                        isMobile 
                          ? 'px-2 py-1.5 text-xs min-w-0' 
                          : 'px-3 py-2 text-sm'
                      } border-primary/20 hover:border-primary/40 transition-colors`}
                    >
                      <div className="flex items-center">
                        {chain.hasIcon && (
                          <div
                            className={`${
                              isMobile ? 'w-3 h-3 mr-1' : 'w-4 h-4 mr-2'
                            } rounded-full overflow-hidden flex-shrink-0`}
                            style={{
                              background: chain.iconBackground,
                            }}
                          >
                            {chain.iconUrl && (
                              <img
                                alt={chain.name ?? 'Chain icon'}
                                src={chain.iconUrl}
                                className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'}`}
                              />
                            )}
                          </div>
                        )}
                        {!isMobile && (
                          <span className="truncate">{chain.name}</span>
                        )}
                      </div>
                    </Button>

                    <Button
                      onClick={() => {
                        openAccountModal();
                        onModalOpen?.();
                      }}
                      size="sm"
                      className={`${
                        isMobile 
                          ? 'px-2 py-1.5 text-xs flex-1 min-w-0' 
                          : 'px-3 py-2 text-sm'
                      } bg-gradient-primary hover:opacity-90 glow-primary transition-all duration-200`}
                    >
                      <div className={`flex ${
                        isMobile 
                          ? 'flex-col items-center justify-center' 
                          : 'items-center space-x-2'
                      } w-full`}>
                        <span className={`font-medium truncate ${
                          isMobile ? 'text-xs leading-tight' : 'text-sm'
                        }`}>
                          {isMobile 
                            ? `${account.displayName?.slice(0, 4)}...${account.displayName?.slice(-2)}` 
                            : account.displayName
                          }
                        </span>
                        {account.displayBalance && (
                          <span className={`${
                            isMobile 
                              ? 'text-[10px] opacity-75 leading-tight' 
                              : 'text-xs'
                          } text-muted-foreground truncate`}>
                            {isMobile 
                              ? account.displayBalance.split(' ')[0] 
                              : `(${account.displayBalance})`}
                          </span>
                        )}
                      </div>
                    </Button>
                  </div>
                );
              })()}
            </div>
          );
        }}
      </ConnectButton.Custom>
    </div>
  );
};