"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Wallet, Database, Network, Plus, Send } from "lucide-react"
import { web3Client } from "@/lib/web3-client"
import { config } from "@/lib/config"

export function Web3Integration() {
  const [isConnected, setIsConnected] = useState(false)
  const [walletAddress, setWalletAddress] = useState<string>("")
  const [networkStatus, setNetworkStatus] = useState<"connected" | "disconnected" | "connecting">("disconnected")
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null)
  const [sessionName, setSessionName] = useState("")
  const [isCreatingSession, setIsCreatingSession] = useState(false)
  const [isSubmittingTask, setIsSubmittingTask] = useState(false)
  const [taskMessage, setTaskMessage] = useState("")

  useEffect(() => {
    checkConnection()
  }, [])

  const checkConnection = async () => {
    if (web3Client.isConnected()) {
      const address = await web3Client.getAddress()
      if (address) {
        setIsConnected(true)
        setWalletAddress(address)
        setNetworkStatus("connected")
      }
    }
  }

  const connectWallet = async () => {
    setNetworkStatus("connecting")
    try {
      const address = await web3Client.connectWallet()
      if (address) {
        setIsConnected(true)
        setWalletAddress(address)
        setNetworkStatus("connected")
      } else {
        setNetworkStatus("disconnected")
      }
    } catch (error) {
      console.error("Connection failed:", error)
      setNetworkStatus("disconnected")
    }
  }

  const createSession = async () => {
    if (!sessionName.trim() || !isConnected) return

    setIsCreatingSession(true)
    try {
      const sessionData = {
        name: sessionName,
        metadata: JSON.stringify({
          createdAt: new Date().toISOString(),
          version: config.app.version,
        }),
        userAddress: walletAddress,
        config: 1, // Default config
      }

      const sessionId = await web3Client.createSession(sessionData)
      if (sessionId !== null) {
        setCurrentSessionId(sessionId)
        setSessionName("")
        console.log("Session created with ID:", sessionId)
      }
    } catch (error) {
      console.error("Failed to create session:", error)
    } finally {
      setIsCreatingSession(false)
    }
  }

  const submitTask = async () => {
    if (!taskMessage.trim() || !currentSessionId || !isConnected) return

    setIsSubmittingTask(true)
    try {
      const taskData = {
        sessionId: currentSessionId,
        message: taskMessage,
        timestamp: Date.now(),
        userAddress: walletAddress,
      }

      const taskId = await web3Client.submitTask(taskData)
      if (taskId !== null) {
        setTaskMessage("")
        console.log("Task submitted with ID:", taskId)
      }
    } catch (error) {
      console.error("Failed to submit task:", error)
    } finally {
      setIsSubmittingTask(false)
    }
  }

  if (!config.web3.enabled) {
    return null
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5" />
          Web3 Blockchain Integration
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-sm">Network Status:</span>
          <Badge variant={networkStatus === "connected" ? "default" : "secondary"}>
            <Network className="h-3 w-3 mr-1" />
            {networkStatus}
          </Badge>
        </div>

        {isConnected ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Wallet className="h-4 w-4" />
              <span className="text-sm font-mono">
                {walletAddress.slice(0, 6)}...{walletAddress.slice(-4)}
              </span>
            </div>

            {/* Session Creation */}
            <div className="space-y-2">
              <Label htmlFor="sessionName">Create New Session</Label>
              <div className="flex gap-2">
                <Input
                  id="sessionName"
                  value={sessionName}
                  onChange={(e) => setSessionName(e.target.value)}
                  placeholder="Enter session name"
                  className="flex-1"
                />
                <Button onClick={createSession} disabled={!sessionName.trim() || isCreatingSession} size="sm">
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Current Session */}
            {currentSessionId && (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm">Current Session:</span>
                  <Badge variant="outline">#{currentSessionId}</Badge>
                </div>

                {/* Task Submission */}
                <div className="space-y-2">
                  <Label htmlFor="taskMessage">Submit Task</Label>
                  <div className="flex gap-2">
                    <Input
                      id="taskMessage"
                      value={taskMessage}
                      onChange={(e) => setTaskMessage(e.target.value)}
                      placeholder="Enter chat message"
                      className="flex-1"
                    />
                    <Button onClick={submitTask} disabled={!taskMessage.trim() || isSubmittingTask} size="sm">
                      <Send className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            )}

            <div className="text-xs text-muted-foreground space-y-1">
              <p>SessionV2: {config.web3.sessionV2Address?.slice(0, 10)}...</p>
              <p>QueueV2: {config.web3.sessionQueueV2Address?.slice(0, 10)}...</p>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            <Button onClick={connectWallet} className="w-full" disabled={networkStatus === "connecting"}>
              <Wallet className="h-4 w-4 mr-2" />
              {networkStatus === "connecting" ? "Connecting..." : "Connect Wallet"}
            </Button>
            <p className="text-xs text-muted-foreground">Connect your wallet to enable blockchain storage</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
