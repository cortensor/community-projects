import  { useState } from 'react';
import { CortensorChatWeb2 } from './mainWeb2';
import { CortensorChatWeb3 } from './mainWeb3';


// import { CortensorChatWeb3 } from './mainWeb3'
// import { CortensorChatWeb2 } from './mainWeb2'
type TabType = 'web2' | 'web3';

const Dashboard = () => {
  const [activeTab, setActiveTab] = useState<TabType>('web2');

  return (
    <div className="flex flex-col h-screen bg-background neural-bg pt-16">
      {/* Header with Custom Glassmorphism Tabs - Compact Design */}
      <div className="flex-shrink-0 p-1 sm:p-1.5">
        <div className="glass rounded-lg p-0.5 flex space-x-0.5 max-w-xs mx-auto">
          <button
            onClick={() => setActiveTab('web2')}
            className={`
              flex-1 px-3 py-2 rounded-md text-xs font-semibold transition-all duration-300
              ${activeTab === 'web2'
                ? 'bg-gradient-to-r from-primary/20 to-secondary/20 text-primary glow-primary border border-primary/30'
                : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
              }
            `}
          >
            <div className="flex items-center justify-center space-x-1.5">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              <span>Web2</span>
            </div>
          </button>
          
          <button
            onClick={() => setActiveTab('web3')}
            className={`
              flex-1 px-3 py-2 rounded-md text-xs font-semibold transition-all duration-300
              ${activeTab === 'web3'
                ? 'bg-gradient-to-r from-accent/20 to-primary/20 text-accent glow-accent border border-accent/30'
                : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
              }
            `}
          >
            <div className="flex items-center justify-center space-x-1.5">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span>Web3</span>
            </div>
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full transition-all duration-500 ease-in-out">
          {activeTab === 'web2' && (
            <div className="h-full animate-in fade-in-50 duration-300">
              <CortensorChatWeb2 />
            </div>
          )}
          {activeTab === 'web3' && (
            <div className="h-full animate-in fade-in-50 duration-300">
              <CortensorChatWeb3 />
            </div>
          )}
        </div>
      </div>

    </div>
  );
};

export default Dashboard;