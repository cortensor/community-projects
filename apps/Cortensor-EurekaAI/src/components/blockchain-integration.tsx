"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Database, Plus, Send, CheckCircle, XCircle } from "lucide-react"

export function BlockchainIntegration() {
  const [sessionName, setSessionName] = useState("")
  const [userAddress, setUserAddress] = useState("")
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null)
  const [taskMessage, setTaskMessage] = useState("")
  const [isCreatingSession, setIsCreatingSession] = useState(false)
  const [isSubmittingTask, setIsSubmittingTask] = useState(false)
  const [lastResult, setLastResult] = useState<{ type: "success" | "error"; message: string } | null>(null)

  const createSession = async () => {
    if (!sessionName.trim() || !userAddress.trim()) return

    setIsCreatingSession(true)
    setLastResult(null)

    try {
      const response = await fetch("/api/blockchain/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: sessionName,
          userAddress,
          metadata: JSON.stringify({
            createdAt: new Date().toISOString(),
            source: "frontend",
          }),
        }),
      })

      const data = await response.json()

      if (data.success && data.sessionId) {
        setCurrentSessionId(data.sessionId)
        setSessionName("")
        setLastResult({
          type: "success",
          message: `Session created with ID: ${data.sessionId}`,
        })
      } else {
        setLastResult({
          type: "error",
          message: data.error || "Failed to create session",
        })
      }
    } catch (error) {
      setLastResult({
        type: "error",
        message: "Network error occurred",
      })
    } finally {
      setIsCreatingSession(false)
    }
  }

  const submitTask = async () => {
    if (!taskMessage.trim() || !currentSessionId || !userAddress.trim()) return

    setIsSubmittingTask(true)
    setLastResult(null)

    try {
      const response = await fetch("/api/blockchain/task", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sessionId: currentSessionId,
          message: taskMessage,
          userAddress,
        }),
      })

      const data = await response.json()

      if (data.success && data.taskId) {
        setTaskMessage("")
        setLastResult({
          type: "success",
          message: `Task submitted with ID: ${data.taskId}`,
        })
      } else {
        setLastResult({
          type: "error",
          message: data.error || "Failed to submit task",
        })
      }
    } catch (error) {
      setLastResult({
        type: "error",
        message: "Network error occurred",
      })
    } finally {
      setIsSubmittingTask(false)
    }
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5" />
          Blockchain Integration
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* User Address Input */}
        <div className="space-y-2">
          <Label htmlFor="userAddress">User Address</Label>
          <Input
            id="userAddress"
            value={userAddress}
            onChange={(e) => setUserAddress(e.target.value)}
            placeholder="0x..."
            className="font-mono text-sm"
          />
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
            <Button
              onClick={createSession}
              disabled={!sessionName.trim() || !userAddress.trim() || isCreatingSession}
              size="sm"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Current Session */}
        {currentSessionId && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Current Session:</span>
              <Badge variant="outline">#{currentSessionId}</Badge>
            </div>

            {/* Task Submission */}
            <div className="space-y-2">
              <Label htmlFor="taskMessage">Submit Task</Label>
              <Textarea
                id="taskMessage"
                value={taskMessage}
                onChange={(e) => setTaskMessage(e.target.value)}
                placeholder="Enter chat message or task data"
                className="min-h-[80px]"
              />
              <Button
                onClick={submitTask}
                disabled={!taskMessage.trim() || !userAddress.trim() || isSubmittingTask}
                className="w-full"
              >
                <Send className="h-4 w-4 mr-2" />
                {isSubmittingTask ? "Submitting..." : "Submit Task"}
              </Button>
            </div>
          </div>
        )}

        {/* Result Display */}
        {lastResult && (
          <div
            className={`flex items-center gap-2 p-3 rounded-md text-sm ${
              lastResult.type === "success" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
            }`}
          >
            {lastResult.type === "success" ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
            <span>{lastResult.message}</span>
          </div>
        )}

        <div className="text-xs text-muted-foreground">
          <p>• All blockchain interactions are handled securely by the backend</p>
          <p>• No wallet connection required from users</p>
          <p>• Connected to Arbitrum Sepolia network</p>
        </div>
      </CardContent>
    </Card>
  )
}
