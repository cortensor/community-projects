'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import {
  Activity,
  Clock,
  Users,
  CheckCircle,
  AlertCircle,
  Zap,
  Trash2,
  Eye,
  EyeOff
} from 'lucide-react'
import {
  useWatchSessionV2SessionCreatedEvent,
  useWatchSessionV2TaskSubmittedEvent,
  useWatchSessionQueueV2TaskQueuedEvent,
  useWatchSessionQueueV2TaskAssignedEvent,
  useWatchSessionQueueV2TaskEndedEvent
} from '@/generated'
import { formatDistanceToNow } from 'date-fns'
import { useAccount } from 'wagmi'

interface BlockchainEvent {
  id: string
  type: 'SessionCreated' | 'TaskSubmitted' | 'TaskQueued' | 'TaskAssigned' | 'TaskEnded'
  timestamp: Date
  data: any
  transactionHash?: string
  blockNumber?: bigint
}

interface EventMonitorProps {
  className?: string
}

export function EventMonitor({ className }: EventMonitorProps) {
  const { address } = useAccount()
  const [events, setEvents] = useState<BlockchainEvent[]>([])
  const [isVisible, setIsVisible] = useState(true)
  const [maxEvents] = useState(50) // Limit to prevent memory issues
  const [isWatchingEnabled, setIsWatchingEnabled] = useState(true)

  // Cleanup function to prevent memory leaks
  useEffect(() => {
    return () => {
      setEvents([])
      setIsWatchingEnabled(false)
    }
  }, [])

  const addEvent = (type: BlockchainEvent['type'], data: any, transactionHash?: string, blockNumber?: bigint) => {
    const newEvent: BlockchainEvent = {
      id: `${type}-${Date.now()}-${Math.random()}`,
      type,
      timestamp: new Date(),
      data,
      transactionHash,
      blockNumber
    }

    setEvents(prev => {
      const updated = [newEvent, ...prev]
      return updated.slice(0, maxEvents) // Keep only the latest events
    })
  }

  // Watch for SessionCreated events
  useWatchSessionV2SessionCreatedEvent({
    enabled: isWatchingEnabled && !!address,
    onLogs(logs) {
      logs.forEach((log) => {
        if (log.args.owner === address) {
          addEvent('SessionCreated', {
            sessionId: Number(log.args.sessionId),
            sid: log.args.sid,
            owner: log.args.owner,
            miners: log.args.miners
          }, log.transactionHash, log.blockNumber)
        }
      })
    },
  })

  // Watch for TaskSubmitted events
  useWatchSessionV2TaskSubmittedEvent({
    enabled: isWatchingEnabled,
    onLogs(logs) {
      logs.forEach((log) => {
        // TaskSubmitted events don't have a user/owner field, so we'll monitor all events
        // You may want to filter by sessionId if you have access to user's sessions
        addEvent('TaskSubmitted', {
          sessionId: Number(log.args.sessionId),
          taskId: Number(log.args.taskId),
          taskData: log.args.taskData,
          clientReference: log.args.clientReference
        }, log.transactionHash, log.blockNumber)
      })
    },
  })

  // Watch for TaskQueued events
  useWatchSessionQueueV2TaskQueuedEvent({
    enabled: isWatchingEnabled,
    onLogs(logs) {
      logs.forEach((log) => {
        addEvent('TaskQueued', {
          sessionId: Number(log.args.sessionId),
          taskId: Number(log.args.taskId),
          globalId: Number(log.args.globalId)
        }, log.transactionHash, log.blockNumber)
      })
    },
  })

  // Watch for TaskAssigned events
  useWatchSessionQueueV2TaskAssignedEvent({
    enabled: isWatchingEnabled,
    onLogs(logs) {
      logs.forEach((log) => {
        addEvent('TaskAssigned', {
          sessionId: Number(log.args.sessionId),
          taskId: Number(log.args.taskId),
          miners: log.args.miners as string[]
        }, log.transactionHash, log.blockNumber)
      })
    },
  })

  // Watch for TaskEnded events
  useWatchSessionQueueV2TaskEndedEvent({
    enabled: isWatchingEnabled,
    onLogs(logs) {
      logs.forEach((log) => {
        addEvent('TaskEnded', {
          sessionId: Number(log.args.sessionId),
          taskId: Number(log.args.taskId)
        }, log.transactionHash, log.blockNumber)
      })
    },
  })

  const getEventIcon = (type: BlockchainEvent['type']) => {
    switch (type) {
      case 'SessionCreated':
        return <Zap className="h-4 w-4 text-blue-500" />
      case 'TaskSubmitted':
        return <Clock className="h-4 w-4 text-yellow-500" />
      case 'TaskQueued':
        return <Activity className="h-4 w-4 text-orange-500" />
      case 'TaskAssigned':
        return <Users className="h-4 w-4 text-purple-500" />
      case 'TaskEnded':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />
    }
  }

  const getEventBadgeVariant = (type: BlockchainEvent['type']) => {
    switch (type) {
      case 'SessionCreated':
        return 'default'
      case 'TaskSubmitted':
        return 'secondary'
      case 'TaskQueued':
        return 'outline'
      case 'TaskAssigned':
        return 'secondary'
      case 'TaskEnded':
        return 'default'
      default:
        return 'outline'
    }
  }

  const formatEventData = (event: BlockchainEvent) => {
    switch (event.type) {
      case 'SessionCreated':
        return `Session #${event.data.sessionId} created with ${event.data.nodeCount} nodes`
      case 'TaskSubmitted':
        return `Task #${event.data.taskId} submitted to session #${event.data.sessionId}`
      case 'TaskQueued':
        return `Task #${event.data.taskId} queued (Global ID: ${event.data.globalId})`
      case 'TaskAssigned':
        return `Task #${event.data.taskId} assigned to ${event.data.miners?.length || 0} miners`
      case 'TaskEnded':
        return `Task #${event.data.taskId} completed`
      default:
        return 'Unknown event'
    }
  }

  const clearEvents = () => {
    setEvents([])
  }

  if (!isVisible) {
    return (
      <div className={className}>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsVisible(true)}
          className="w-full"
        >
          <Eye className="h-4 w-4 mr-2" />
          Show Event Monitor
        </Button>
      </div>
    )
  }

  return (
    <div className={className}>
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              <CardTitle className="text-lg">Event Monitor</CardTitle>
              <Badge variant="outline" className="text-xs">
                {events.length} events
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={clearEvents}
                disabled={events.length === 0}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsVisible(false)}
              >
                <EyeOff className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {events.length === 0 ? (
            <div className="text-center py-8">
              <Activity className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">
                No blockchain events yet. Events will appear here in real-time.
              </p>
            </div>
          ) : (
            <ScrollArea className="h-[400px]">
              <div className="space-y-3">
                {events.map((event, index) => (
                  <div key={event.id}>
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 mt-0.5">
                        {getEventIcon(event.type)}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge
                            variant={getEventBadgeVariant(event.type)}
                            className="text-xs"
                          >
                            {event.type}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {formatDistanceToNow(event.timestamp, { addSuffix: true })}
                          </span>
                        </div>

                        <p className="text-sm">
                          {formatEventData(event)}
                        </p>

                        {event.transactionHash && (
                          <p className="text-xs text-muted-foreground mt-1 font-mono">
                            Tx: {event.transactionHash.slice(0, 10)}...{event.transactionHash.slice(-8)}
                          </p>
                        )}
                      </div>
                    </div>

                    {index < events.length - 1 && (
                      <Separator className="mt-3" />
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  )
}