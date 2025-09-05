'use client'

import { useState, useCallback } from 'react'
import { CortensorChatWeb3 } from './mainWeb3'
import { CortensorChatWeb2 } from './mainWeb2'
import { Bot, Globe, Zap, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'

type TabType = 'web2' | 'web3'

interface Tab {
  id: TabType
  label: string
  icon: React.ComponentType<{ className?: string }>
  description: string
  badge?: string
}

const MainChatPage = () => {
  const [activeTab, setActiveTab] = useState<TabType>('web2')
  const [hoveredTab, setHoveredTab] = useState<TabType | null>(null)

  const tabs: Tab[] = [
    {
      id: 'web2',
      label: 'Web2 Chat',
      icon: Globe,
      description: 'Traditional AI features with enhanced capabilities',
      badge: 'Classic'
    },
    {
      id: 'web3',
      label: 'Web3 Chat',
      icon: Zap,
      description: 'Blockchain-powered AI with decentralized features',
      badge: 'New'
    }
  ]

  const handleTabChange = useCallback((tabId: TabType) => {
    setActiveTab(tabId)
  }, [])



  return (
    <div className="h-screen bg-background flex flex-col">
      {/* Enhanced Tab Navigation */}
      <div className="sticky top-0 z-50 border-b backdrop-blur-xl bg-background/80 border-border/50 flex-shrink-0">
        <div className="px-2 py-2 mx-auto max-w-4xl sm:px-4 sm:py-3">
          <div className="flex justify-center items-center">
            <div 
              className="flex relative p-0.5 rounded-xl border backdrop-blur-xl bg-card/40 border-border/50 shadow-xl sm:p-1 sm:rounded-2xl"
              role="tablist"
              aria-label="Chat interface tabs"
            >
              {/* Active tab indicator */}
              <div
                className={cn(
                  "absolute inset-y-0.5 rounded-lg bg-gradient-to-r from-primary via-primary/90 to-primary/80 shadow-lg shadow-primary/25 transition-all duration-300 sm:inset-y-1 sm:rounded-xl",
                  activeTab === 'web2' 
                    ? "left-0.5 w-[calc(50%-2px)]" 
                    : "left-[calc(50%+1px)] w-[calc(50%-2px)]"
                )}
              />

              {tabs.map((tab) => {
                const Icon = tab.icon
                const isActive = activeTab === tab.id
                const isHovered = hoveredTab === tab.id

                return (
                  <button
                    key={tab.id}
                    onClick={() => handleTabChange(tab.id)}
                    onMouseEnter={() => setHoveredTab(tab.id)}
                    onMouseLeave={() => setHoveredTab(null)}
                    className={cn(
                      "relative z-10 flex items-center space-x-1.5 px-2 py-2 rounded-lg transition-all duration-300 font-medium",
                      "sm:space-x-2 sm:px-4 sm:py-3 sm:rounded-xl",
                      "focus:outline-none focus:ring-2 focus:ring-primary/20 focus:ring-offset-2",
                      isActive
                        ? "text-primary-foreground"
                        : "text-foreground hover:text-foreground/80"
                    )}
                    role="tab"
                    id={`tab-${tab.id}`}
                  >
                    {/* Icon */}
                    <div className={cn(
                      "transition-all duration-300",
                      isActive ? "scale-110" : "scale-100"
                    )}>
                      <Icon 
                        className={cn(
                          "w-4 h-4 transition-all duration-300 sm:w-5 sm:h-5",
                          isActive 
                            ? "text-primary-foreground drop-shadow-lg" 
                            : "text-foreground hover:text-foreground/80"
                        )} 
                      />
                    </div>

                    {/* Tab content */}
                    <div className="text-left">
                      <div className="flex items-center space-x-1 sm:space-x-2">
                        <span className={cn(
                          "text-xs font-semibold transition-all duration-300 sm:text-sm",
                          isActive ? "text-primary-foreground" : "text-foreground"
                        )}>
                          {tab.label}
                        </span>
                        {tab.badge && (
                          <span
                            className={cn(
                              "px-1.5 py-0.5 text-xs font-medium rounded-full hidden sm:inline-block sm:px-2",
                              isActive 
                                ? "bg-primary-foreground/20 text-primary-foreground" 
                                : "bg-muted text-foreground/80"
                            )}
                          >
                            {tab.badge}
                          </span>
                        )}
                      </div>
                      <div className={cn(
                        "text-xs transition-all duration-300 hidden lg:block",
                        isActive 
                          ? "text-primary-foreground/80" 
                          : "text-foreground/70"
                      )}>
                        {tab.description}
                      </div>
                    </div>

                    {/* Hover effect indicator */}
                    {isHovered && !isActive && (
                      <div
                        className="absolute inset-0 rounded-lg bg-foreground/10 sm:rounded-xl transition-opacity duration-200"
                      />
                    )}
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Tab Content */}
      <div className="relative flex-1 min-h-0 overflow-hidden">
        <div className="h-full w-full">
          {activeTab === 'web3' ? (
            <CortensorChatWeb3 />
          ) : (
            <CortensorChatWeb2 />
          )}
        </div>
      </div>

      {/* Optional: Floating action indicator */}
      <div className="fixed bottom-4 right-4 z-40 sm:bottom-6 sm:right-6 opacity-100">
        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-card/80 backdrop-blur-xl border border-border/50 shadow-lg sm:px-4 sm:py-2">
          <Sparkles className="w-3 h-3 text-primary animate-pulse sm:w-4 sm:h-4" />
          <span className="text-xs font-medium text-foreground sm:text-sm">
            {activeTab === 'web3' ? 'Web3 Mode' : 'Web2 Mode'}
          </span>
        </div>
      </div>
    </div>
  )
}

export default MainChatPage
