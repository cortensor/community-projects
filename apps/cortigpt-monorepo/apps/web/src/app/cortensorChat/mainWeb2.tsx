'use client'

import { useAccount } from 'wagmi'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ConnectWalletButton } from '@/components/ui/connect-wallet-button'
import { Wallet, Zap, Menu } from 'lucide-react'
import { useState, useEffect } from 'react'
import {
    Credenza,
    CredenzaBody,
    CredenzaClose,
    CredenzaContent,
    CredenzaDescription,
    CredenzaFooter,
    CredenzaHeader,
    CredenzaTitle,
    CredenzaTrigger,
} from '@/components/ui/credenza'
import { Button } from '@/components/ui/button'
import { motion, AnimatePresence } from 'framer-motion'
import { useIsMobile } from '@/hooks/use-mobile'
import { ChatInterface } from './web2Components/ChatInterface'
import { ChatHistory } from './web2Components/ChatHistory'
import { cn } from '@/lib/utils'

export function CortensorChatWeb2() {
    const { address, isConnected } = useAccount()
    const [showWalletPrompt, setShowWalletPrompt] = useState(false)
    const [userId, setUserId] = useState<string | null>(null)
    const isMobile = useIsMobile()

    // Generate or retrieve user ID
    useEffect(() => {
        const storedUserId = localStorage.getItem('cortensor_user_id')
        
        if (isConnected && address) {
            // If wallet is connected, use wallet address as user ID
            setUserId(address)
        } else if (storedUserId) {
            // If user ID exists in localStorage, use it
            setUserId(storedUserId)
        } else {
            // Show wallet connection prompt if no user ID and not connected
            setShowWalletPrompt(true)
            // Generate a fallback user ID after a short delay if no action is taken
            const fallbackTimer = setTimeout(() => {
                if (!userId) {
                    generateRandomUserId()
                }
            }, 3000) // 3 second delay
            
            return () => clearTimeout(fallbackTimer)
        }
    }, [isConnected, address, userId])

    // Generate random user ID and store in localStorage
    const generateRandomUserId = () => {
        const randomId = `user_${Math.random().toString(36).substr(2, 9)}_${Date.now()}`
        localStorage.setItem('cortensor_user_id', randomId)
        setUserId(randomId)
        setShowWalletPrompt(false)
    }

    // Handle wallet connection
    const handleWalletConnect = () => {
        setShowWalletPrompt(false)
        // The wallet connection will be handled by the ConnectWalletButton
        // and the useEffect will update the userId when address changes
    }

    return (
        <div className="flex flex-col h-full bg-background">
            {/* Wallet Connection Prompt Credenza */}
            <Credenza open={showWalletPrompt} onOpenChange={setShowWalletPrompt}>
                <CredenzaContent className="backdrop-blur-xl bg-card/95 border-border/50 shadow-glass">
                    <CredenzaHeader>
                        <div className="flex items-center space-x-3">
                            <div className="flex justify-center items-center w-12 h-12 rounded-full bg-gradient-primary shadow-glow-primary">
                                <Wallet className="w-6 h-6 text-primary-foreground" />
                            </div>
                            <div>
                                <CredenzaTitle className="text-xl font-futura text-foreground">
                                    Connect Your Wallet
                                </CredenzaTitle>
                                <CredenzaDescription className="text-muted-foreground">
                                    Connect your wallet to track your messages and get a personalized experience
                                </CredenzaDescription>
                            </div>
                        </div>
                    </CredenzaHeader>
                    <CredenzaBody className="space-y-4">
                        <div className="p-4 rounded-lg border bg-muted/50 border-border/50">
                            <h4 className="mb-2 font-medium text-foreground">Why connect your wallet?</h4>
                            <ul className="space-y-1 text-sm text-muted-foreground">
                                <li>• Track your conversation history</li>
                                <li>• Personalized AI responses</li>
                                <li>• Secure and decentralized</li>
                                <li>• Access to premium features</li>
                            </ul>
                        </div>
                        <div className="flex justify-center items-center space-x-2 text-sm text-muted-foreground">
                            <Zap className="w-4 h-4" />
                            <span>Secure • Decentralized • Private</span>
                        </div>
                    </CredenzaBody>
                    <CredenzaFooter className="flex flex-col space-y-2 sm:flex-row sm:space-y-0 sm:space-x-2">
                        <ConnectWalletButton 
                            className="flex-1" 
                        />
                        <Button 
                            variant="outline" 
                            className="flex-1" 
                            onClick={generateRandomUserId}
                        >
                            Continue Without Wallet
                        </Button>
                    </CredenzaFooter>
                </CredenzaContent>
            </Credenza>

            {/* Header - Sleek & Responsive */}
            <motion.header
                className="flex-shrink-0 border-b bg-card/80 backdrop-blur-sm"
                initial={{ y: -100 }}
                animate={{ y: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
            >
                <div className="px-2 py-1.5 mx-auto max-w-7xl sm:px-4 sm:py-2">
                    <div className="flex justify-between items-center min-w-0">
                        <div className="flex gap-1.5 items-center min-w-0 sm:gap-2">
                            <motion.div
                                className="flex justify-center items-center w-5 h-5 rounded-full sm:w-6 sm:h-6 bg-primary/10 flex-shrink-0"
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                            >
                                <img src="/cortigpt-4.png" alt="CortiGPT" className="w-4 h-4 sm:w-5 sm:h-5" />
                            </motion.div>
                            <div className="min-w-0">
                                <h1 className="text-xs font-semibold truncate sm:text-sm">CortiGPT Web2</h1>
                                <p className="hidden text-xs text-muted-foreground truncate md:block">
                                    Traditional AI Chat
                                </p>
                            </div>
                        </div>

                        {/* User Info - Compact */}
                        <div className="flex gap-1 items-center text-xs flex-shrink-0">
                            <div className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                            <span className="font-mono text-xs max-w-20 truncate">
                                {isConnected && address 
                                    ? `${address.slice(0, 4)}...${address.slice(-2)}`
                                    : userId ? `${userId.slice(0, 8)}...` : 'Guest'
                                }
                            </span>
                        </div>
                    </div>
                </div>
            </motion.header>

            {/* Main Content - Fixed Height Layout */}
            <main className="flex flex-col flex-1 min-h-0">
                <AnimatePresence mode="wait">
                    {!isMobile && (
                        <motion.div
                            key="desktop-layout"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex flex-1 gap-2 p-2 min-h-0 sm:gap-4 sm:p-4"
                        >
                            {/* Chat History Sidebar - Desktop */}
                            <motion.div
                                className="w-80 min-h-0"
                                initial={{ x: -50, opacity: 0 }}
                                animate={{ x: 0, opacity: 1 }}
                                transition={{ delay: 0.1 }}
                            >
                              {userId && <ChatHistory className="h-full" userAddress={userId} />}
                            </motion.div>

                                            {/* Chat Interface - Desktop */}
                            <motion.div
                                className="flex-1 min-h-0"
                                initial={{ y: 50, opacity: 0 }}
                                animate={{ y: 0, opacity: 1 }}
                                transition={{ delay: 0.2 }}
                            >
                                {userId ? (
                                    <ChatInterface className="h-full" userAddress={userId} />
                                ) : (
                                    <Card className="h-full backdrop-blur-xl bg-card/50 border-border/50 shadow-glass">
                                        <CardContent className="flex items-center justify-center h-full">
                                            <div className="text-center">
                                                <img src="/cortigpt-4.png" alt="CortiGPT" className="w-24 h-24 mx-auto mb-4" />
                                                <p className="text-muted-foreground">Initializing Cortensor Chat...</p>
                                            </div>
                                        </CardContent>
                                    </Card>
                                )}
                            </motion.div>
                        </motion.div>
                    )}

                    {/* Mobile Layout */}
                    {isMobile && (
                        <motion.div
                            key="mobile-layout"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex relative flex-col flex-1 min-h-0"
                        >
                            {/* Mobile Chat Interface - Full Width */}
                            <div className="flex-1 min-h-0">
                                {userId ? (
                                    <ChatInterface className="h-full" userAddress={userId} />
                                ) : (
                                    <Card className="h-full backdrop-blur-xl bg-card/50 border-border/50 shadow-glass">
                                        <CardContent className="flex items-center justify-center h-full">
                                            <div className="text-center">
                                                <img src="/cortigpt-4.png" alt="CortiGPT" className="w-12 h-12 mx-auto mb-4" />
                                                <p className="text-muted-foreground">Initializing Cortensor Chat...</p>
                                            </div>
                                        </CardContent>
                                    </Card>
                                )}
                            </div>

                            {/* Floating Chat History Button */}
                            <div className="fixed right-4 bottom-20 z-50">
                                <Credenza>
                                    <CredenzaTrigger asChild>
                                        <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                                            <Button
                                                size="sm"
                                                className="w-12 h-12 rounded-full shadow-lg"
                                            >
                                                <Menu className="w-5 h-5" />
                                            </Button>
                                        </motion.div>
                                    </CredenzaTrigger>
                                    <CredenzaContent className="backdrop-blur-xl bg-card/95 border-border/50 shadow-glass">
                                        <CredenzaHeader>
                                            <CredenzaTitle className="text-lg font-futura text-foreground">
                                                Chat History
                                            </CredenzaTitle>
                                        </CredenzaHeader>
                                        <CredenzaBody className="p-0">
                                            <div className="h-[60vh]">
                                             {userId && <ChatHistory className="h-full" userAddress={userId} />}
                                            </div>
                                        </CredenzaBody>
                                    </CredenzaContent>
                                </Credenza>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </main>
        </div>
    )
}