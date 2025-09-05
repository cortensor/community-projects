'use client'

import { useEffect, useState } from 'react'
import { useAccount } from 'wagmi'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ConnectWalletButton } from '@/components/ui/connect-wallet-button'
import {
    Credenza,
    CredenzaContent,
    CredenzaHeader,
    CredenzaTitle,
    CredenzaTrigger,
    CredenzaClose,
    CredenzaBody,
    CredenzaDescription,
    CredenzaFooter
} from '@/components/ui/credenza'
import { useIsMobile } from '@/hooks/use-mobile'
import {
    Bot,
    Activity,
    Settings,
    Zap,
    Users,
    MessageSquare,
    Grid3X3,
    BarChart3,
    Menu,
    X,
    Square,
    Wallet,
    AlertTriangle,
    Smartphone,
    QrCode
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChatInterface } from './components/ChatInterface'
import { SessionManager } from './components/SessionManager'
import { TaskManager } from './components/TaskManager'
import { EventLogger } from './components/EventLogger'
import { useCortensorSession } from './hooks/useCortensorSession'
import { useCortensorTasks } from './hooks/useCortensorTasks'
import { useSessionStore, useCurrentSession } from './store/useSessionStore'
import { cn } from '@/lib/utils'

export function CortensorChatWeb3() {
    const { address, isConnected } = useAccount()
    const { currentSession, userSessions, isLoadingSessions } = useCortensorSession()
    const { tasks, messages } = useCortensorTasks()
    const { setSessionDialogOpen } = useSessionStore()
    const currentSessionFromStore = useCurrentSession()
    const isMobile = useIsMobile()

    // Mobile credenza states
    const [sessionCredenzaOpen, setSessionCredenzaOpen] = useState(false)
    const [taskCredenzaOpen, setTaskCredenzaOpen] = useState(false)
    const [eventCredenzaOpen, setEventCredenzaOpen] = useState(false)
    const [walletCredenzaOpen, setWalletCredenzaOpen] = useState(!isConnected)

    // Auto-open session dialog if no sessions exist and user is connected
    useEffect(() => {
        if (isConnected && !isLoadingSessions && userSessions.length === 0 && !currentSessionFromStore) {
            const timer = setTimeout(() => {
                setSessionDialogOpen(true)
            }, 1000)

            return () => clearTimeout(timer)
        }
    }, [isConnected, isLoadingSessions, userSessions.length, currentSessionFromStore, setSessionDialogOpen])

    // Auto-open wallet credenza when not connected
    useEffect(() => {
        setWalletCredenzaOpen(!isConnected)
    }, [isConnected])

    const activeTasks = tasks.filter(task =>
        task.status !== 'completed' && task.status !== 'failed'
    )
    const completedTasks = tasks.filter(task => task.status === 'completed')

    if (!isConnected) {
        return (
            <div className="flex justify-center items-center p-4 min-h-screen bg-background">
                {/* Wallet Connection Credenza */}
                <Credenza open={walletCredenzaOpen} onOpenChange={setWalletCredenzaOpen}>
                    <CredenzaContent className="backdrop-blur-xl bg-card/95 border-border/50 shadow-glass">
                        <CredenzaHeader>
                            <div className="flex items-center space-x-3">
                                <div className="flex justify-center items-center w-12 h-12 rounded-full bg-gradient-to-r from-red-500/20 to-orange-500/20 border-2 border-red-500/30">
                                    <AlertTriangle className="w-6 h-6 text-red-500" />
                                </div>
                                <div>
                                    <CredenzaTitle className="text-xl font-bold text-foreground flex items-center gap-2">
                                        <span className="text-red-500">⚠️ Wallet Connection Required</span>
                                    </CredenzaTitle>
                                    <CredenzaDescription className="text-muted-foreground">
                                        Connect your wallet to access CortiGPT AI services
                                    </CredenzaDescription>
                                </div>
                            </div>
                        </CredenzaHeader>
                        <CredenzaBody className="space-y-4">
                            {/* Chrome Extension Limitation Warning */}
                            <div className="p-4 rounded-lg border-2 border-red-500/30 bg-red-500/10">
                                <div className="flex items-start gap-3">
                                    <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                                    <div>
                                        <h4 className="font-semibold text-red-500 mb-2">🚨 IMPORTANT: Chrome Extension Limitations</h4>
                                        <div className="text-sm text-red-600 space-y-2">
                                            <p className="font-medium">❌ Your browser extension wallets (MetaMask, etc.) cannot be used directly in this Chrome extension due to security restrictions.</p>
                                            <p className="font-medium text-orange-600">✅ SOLUTION: Use your mobile wallet instead!</p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Mobile Wallet Instructions */}
                            <div className="p-4 rounded-lg border bg-blue-500/10 border-blue-500/30">
                                <div className="flex items-start gap-3">
                                    <Smartphone className="w-5 h-5 text-blue-500 mt-0.5" />
                                    <div>
                                        <h4 className="font-semibold text-blue-500 mb-2">📱 Connect with Mobile Wallet</h4>
                                        <ul className="text-sm text-blue-600 space-y-1">
                                            <li className="flex items-center gap-2">
                                                <QrCode className="w-4 h-4" />
                                                <span>Scan QR code with your mobile wallet</span>
                                            </li>
                                            <li>• Use WalletConnect or similar protocols</li>
                                            <li>• Works with MetaMask Mobile, Trust Wallet, etc.</li>
                                            <li>• Secure and decentralized connection</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>

                            {/* Features */}
                            <div className="p-4 rounded-lg border bg-muted/50 border-border/50">
                                <h4 className="mb-2 font-medium text-foreground">🚀 What you'll get:</h4>
                                <ul className="space-y-1 text-sm text-muted-foreground">
                                    <li className="flex gap-2 items-center">
                                        <Zap className="w-4 h-4 text-yellow-500" />
                                        <span>Decentralized AI inference</span>
                                    </li>
                                    <li className="flex gap-2 items-center">
                                        <Users className="w-4 h-4 text-green-500" />
                                        <span>Powered by miner network</span>
                                    </li>
                                    <li className="flex gap-2 items-center">
                                        <MessageSquare className="w-4 h-4 text-blue-500" />
                                        <span>Real-time blockchain events</span>
                                    </li>
                                    <li className="flex gap-2 items-center">
                                        <Bot className="w-4 h-4 text-purple-500" />
                                        <span>Advanced AI chat capabilities</span>
                                    </li>
                                </ul>
                            </div>
                        </CredenzaBody>
                        <CredenzaFooter className="flex flex-col space-y-3">
                            <div className="text-center">
                                <p className="text-xs text-red-500 font-medium mb-2">🔴 Remember: Use your MOBILE wallet, not browser extensions!</p>
                            </div>
                            <ConnectWalletButton className="w-full" />
                            <p className="text-xs text-center text-muted-foreground">
                                Having trouble? Make sure WalletConnect is enabled in your mobile wallet
                            </p>
                        </CredenzaFooter>
                    </CredenzaContent>
                </Credenza>
                
                {/* Fallback content when credenza is closed */}
                <Card className="w-full">
                    <CardHeader className="text-center">
                        <div className="flex justify-center items-center mx-auto mb-4 w-12 h-12 rounded-full bg-primary/10">
                            <Bot className="w-6 h-6 text-primary" />
                        </div>
                        <CardTitle className="text-2xl">CortiGPT</CardTitle>
                        <CardDescription>
                            Connect your wallet to start chatting with AI
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <Button 
                            onClick={() => setWalletCredenzaOpen(true)}
                            className="w-full"
                            variant="outline"
                        >
                            <Wallet className="w-4 h-4 mr-2" />
                            Connect Wallet
                        </Button>
                    </CardContent>
                </Card>
            </div>
        )
    }

    return (
        <div className="flex flex-col h-screen bg-background">
            {/* Header - Responsive */}
            <motion.header
                className="flex-shrink-0 border-b bg-card"
                initial={{ y: -100 }}
                animate={{ y: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
            >
                <div className="container px-1 py-1 mx-auto sm:px-3 sm:py-2">
                    <div className="flex justify-between items-center">
                        <div className="flex gap-1 items-center sm:gap-2">
                            <motion.div
                                className="flex justify-center items-center w-8 h-8 rounded-full sm:w-12 sm:h-12 bg-primary/10"
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                            >
                                <Bot className="w-4 h-4 sm:w-6 sm:h-6 text-primary" />
                            </motion.div>
                            <div>
                                <h1 className="text-xs font-semibold sm:text-lg">CortiGPT</h1>
                                <p className="hidden text-xs text-muted-foreground md:block">
                                    Powered by Cortensor Network
                                </p>
                            </div>
                        </div>

                        <div className="flex gap-1 items-center sm:gap-2">
                            {/* Status Indicators - Responsive */}
                            <div className="hidden gap-1 items-center sm:flex sm:gap-2">
                                {currentSessionFromStore && (
                                    <Badge variant="outline" className="px-1 py-0 text-xs">
                                        <Zap className="mr-1 w-2 h-2" />
                                        <span className="hidden md:inline">Session </span>#{currentSessionFromStore.sessionId}
                                    </Badge>
                                )}

                                {activeTasks.length > 0 && (
                                    <Badge variant="secondary" className="px-1 py-0 text-xs">
                                        <Activity className="mr-1 w-2 h-2" />
                                        {activeTasks.length}<span className="hidden md:inline"> active</span>
                                    </Badge>
                                )}

                                {completedTasks.length > 0 && (
                                    <Badge variant="default" className="hidden px-1 py-0 text-xs md:flex">
                                        <MessageSquare className="mr-1 w-2 h-2" />
                                        {completedTasks.length} completed
                                    </Badge>
                                )}

                                <Badge variant="outline" className="hidden px-1 py-0 text-xs lg:flex">
                                    <Grid3X3 className="mr-1 w-2 h-2" />
                                    {tasks.length} total
                                </Badge>
                            </div>

                            {/* Wallet Info - Responsive */}
                            <div className="flex gap-1 items-center text-xs">
                                <div className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                                <span className="font-mono text-xs">
                                    {address?.slice(0, 3)}...{address?.slice(-2)}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </motion.header>

            {/* Main Content - Fixed Height Layout */}
            <main className="flex flex-col flex-1 min-h-0">
                {/* Desktop Layout */}
                <AnimatePresence mode="wait">
                    {!isMobile && (
                        <motion.div
                            key="desktop-layout"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex flex-1 gap-1 p-1 min-h-0 sm:gap-4 sm:p-4"
                        >
                            {/* Left Panel - Session & Task Management with Max Heights */}
                            <motion.div
                                className="flex flex-col gap-1 w-1/5 min-h-0 sm:gap-4"
                                initial={{ x: -50, opacity: 0 }}
                                animate={{ x: 0, opacity: 1 }}
                                transition={{ delay: 0.1 }}
                            >
                                <div className="max-h-[45vh] min-h-[300px]">
                                    <SessionManager />
                                </div>
                                <div className="max-h-[45vh] min-h-[300px]">
                                    <TaskManager />
                                </div>
                            </motion.div>

                            {/* Center Panel - Chat Interface (80% of available height) */}
                            <motion.div
                                className="flex flex-col flex-1 min-h-0"
                                initial={{ y: 50, opacity: 0 }}
                                animate={{ y: 0, opacity: 1 }}
                                transition={{ delay: 0.2 }}
                            >
                                <div className="h-full">
                                    <ChatInterface className="h-full" />
                                </div>
                            </motion.div>

                            {/* Right Panel - Event Logger & Analytics with Max Heights */}
                            <motion.div
                                className="flex flex-col gap-2 w-1/5 min-h-0 sm:gap-4"
                                initial={{ x: 50, opacity: 0 }}
                                animate={{ x: 0, opacity: 1 }}
                                transition={{ delay: 0.3 }}
                            >
                                <div className="max-h-[60vh] min-h-[400px]">
                                    {!isMobile && <EventLogger />}
                                </div>

                                {/* Quick Stats Card - Compact */}
                                <Card className="flex-shrink-0">
                                    <CardHeader className="p-3 pb-2">
                                        <CardTitle className="flex gap-2 items-center text-xs sm:text-sm">
                                            <BarChart3 className="w-3 h-3 sm:w-4 sm:h-4" />
                                            Stats
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent className="p-3 pt-0">
                                        <div className="grid grid-cols-2 gap-1 text-xs sm:gap-2">
                                            <div className="p-1 text-center rounded sm:p-2 bg-muted">
                                                <div className="text-xs font-semibold text-blue-600">{userSessions.length}</div>
                                                <div className="text-xs text-muted-foreground">Sessions</div>
                                            </div>
                                            <div className="p-1 text-center rounded sm:p-2 bg-muted">
                                                <div className="text-xs font-semibold text-green-600">{messages.length}</div>
                                                <div className="text-xs text-muted-foreground">Messages</div>
                                            </div>
                                            <div className="p-1 text-center rounded sm:p-2 bg-muted">
                                                <div className="text-xs font-semibold text-orange-600">{activeTasks.length}</div>
                                                <div className="text-xs text-muted-foreground">Active</div>
                                            </div>
                                            <div className="p-1 text-center rounded sm:p-2 bg-muted">
                                                <div className="text-xs font-semibold text-purple-600">{completedTasks.length}</div>
                                                <div className="text-xs text-muted-foreground">Complete</div>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            </motion.div>
                        </motion.div>
                    )}

                    {/* Mobile Layout - Full Height Chat */}
                    {isMobile && (
                        <motion.div
                            key="mobile-layout"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex relative flex-col flex-1 min-h-0"
                        >
                            {/* Mobile Chat Interface - Takes full available height */}
                            <div className="flex-1 min-h-0">
                                <ChatInterface className="h-full" />
                            </div>

                            {/* Floating Action Buttons - Smaller and more responsive */}
                            <div className="flex fixed right-4 bottom-4 z-50 flex-col gap-2">
                                <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                                    <Button
                                        onClick={() => setSessionCredenzaOpen(true)}
                                        size="sm"
                                        className="w-10 h-10 rounded-full shadow-lg sm:w-12 sm:h-12"
                                    >
                                        <Menu className="w-4 h-4 sm:w-5 sm:h-5" />
                                    </Button>
                                </motion.div>

                                <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                                    <Button
                                        onClick={() => setTaskCredenzaOpen(true)}
                                        size="sm"
                                        className="w-10 h-10 rounded-full shadow-lg sm:w-12 sm:h-12 bg-secondary hover:bg-secondary/80"
                                    >
                                        <Activity className="w-4 h-4 sm:w-5 sm:h-5" />
                                    </Button>
                                </motion.div>

                                <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                                    <Button
                                        onClick={() => setEventCredenzaOpen(true)}
                                        size="sm"
                                        className="w-10 h-10 rounded-full shadow-lg sm:w-12 sm:h-12 bg-accent hover:bg-accent/80"
                                    >
                                        <BarChart3 className="w-4 h-4 sm:w-5 sm:h-5" />
                                    </Button>
                                </motion.div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </main>

            {/* Mobile Credenzas */}
            {isMobile && (
                <>
                    {/* Session Manager Credenza */}
                    <Credenza open={sessionCredenzaOpen} onOpenChange={setSessionCredenzaOpen}>
                        <CredenzaContent className="max-h-[90vh]">
                            <CredenzaHeader>
                                <CredenzaTitle>Session Manager</CredenzaTitle>
                            </CredenzaHeader>
                            <CredenzaBody>
                                <ScrollArea className="h-[70vh]">
                                    <SessionManager />
                                </ScrollArea>
                            </CredenzaBody>
                        </CredenzaContent>
                    </Credenza>

                    {/* Task Manager Credenza */}
                    <Credenza open={taskCredenzaOpen} onOpenChange={setTaskCredenzaOpen}>
                        <CredenzaContent className="max-h-[90vh]">
                            <CredenzaHeader>
                                <CredenzaTitle>Task Manager</CredenzaTitle>
                            </CredenzaHeader>
                            <CredenzaBody>
                                <ScrollArea className="h-[70vh]">
                                    <TaskManager />
                                </ScrollArea>
                            </CredenzaBody>
                        </CredenzaContent>
                    </Credenza>

                    {/* Event Logger Credenza */}
                    <Credenza open={eventCredenzaOpen} onOpenChange={setEventCredenzaOpen}>
                        <CredenzaContent className="max-h-[90vh]">
                            <CredenzaHeader>
                                <CredenzaTitle>Event Logger</CredenzaTitle>
                            </CredenzaHeader>
                            <CredenzaBody>
                                <ScrollArea className="h-[70vh]">
                                    <div className="space-y-4">
                                        {isMobile && <EventLogger />}

                                        {/* Quick Stats Card */}
                                        <Card>
                                            <CardHeader className="pb-3">
                                                <CardTitle className="flex gap-2 items-center text-sm">
                                                    <BarChart3 className="w-4 h-4" />
                                                    Quick Stats
                                                </CardTitle>
                                            </CardHeader>
                                            <CardContent className="space-y-3">
                                                <div className="grid grid-cols-2 gap-2 text-xs">
                                                    <div className="p-2 text-center rounded bg-muted">
                                                        <div className="font-semibold text-blue-600">{userSessions.length}</div>
                                                        <div className="text-muted-foreground">Sessions</div>
                                                    </div>
                                                    <div className="p-2 text-center rounded bg-muted">
                                                        <div className="font-semibold text-green-600">{messages.length}</div>
                                                        <div className="text-muted-foreground">Messages</div>
                                                    </div>
                                                    <div className="p-2 text-center rounded bg-muted">
                                                        <div className="font-semibold text-orange-600">{activeTasks.length}</div>
                                                        <div className="text-muted-foreground">Active</div>
                                                    </div>
                                                    <div className="p-2 text-center rounded bg-muted">
                                                        <div className="font-semibold text-purple-600">{completedTasks.length}</div>
                                                        <div className="text-muted-foreground">Complete</div>
                                                    </div>
                                                </div>
                                            </CardContent>
                                        </Card>
                                    </div>
                                </ScrollArea>
                            </CredenzaBody>
                        </CredenzaContent>
                    </Credenza>
                </>
            )}


        </div>
    )
}