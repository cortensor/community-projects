'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  Activity,
  ChevronDown,
  ChevronRight,
  Zap,
  CheckCircle,
  Users,
  Clock,
  Trash2,
  Hash,
  ExternalLink
} from 'lucide-react'
import {
  useWatchSessionQueueV2TaskEndedEvent,
  useWatchSessionQueueV2TaskAssignedEvent,
  useWatchSessionV2TaskSubmittedEvent
} from '@/generated'
import { useCurrentSessionId } from '../store/useSessionStore'
import { cn } from '@/lib/utils'

interface BlockchainEvent {
  id: string
  type: 'task_submitted' | 'task_assigned' | 'task_ended' | 'session_created' | 'other'
  title: string
  description: string
  timestamp: Date
  data: any
  blockNumber?: number
  transactionHash?: string
  sessionId?: number
  taskId?: number
}

interface EventLoggerProps {
  className?: string
}

export function EventLogger({ className }: EventLoggerProps) {
  const currentSessionId = useCurrentSessionId()
  const [events, setEvents] = useState<BlockchainEvent[]>([])
  const [isOpen, setIsOpen] = useState(true)
  const [maxEvents] = useState(50) // Keep only last 50 events
  const [isWatchingEnabled, setIsWatchingEnabled] = useState(true)

  // Cleanup function to prevent memory leaks
  useEffect(() => {
    return () => {
      setEvents([])
      setIsWatchingEnabled(false)
    }
  }, [])

  const addEvent = (event: Omit<BlockchainEvent, 'id' | 'timestamp'>) => {
    const newEvent: BlockchainEvent = {
      ...event,
      id: `${event.type}-${Date.now()}-${Math.random()}`,
      timestamp: new Date()
    }

    setEvents(prev => {
      const updated = [newEvent, ...prev]
      return updated.slice(0, maxEvents) // Keep only recent events
    })
  }

  const clearEvents = () => {
    setEvents([])
  }

  // Watch for task submitted events
  useWatchSessionV2TaskSubmittedEvent({
    enabled: isWatchingEnabled,
    onLogs(logs) {
      logs.forEach((log) => {
        if (log.args.sessionId && log.args.taskId) {
          const sessionId = Number(log.args.sessionId)
          const taskId = Number(log.args.taskId)

          addEvent({
            type: 'task_submitted',
            title: 'Task Submitted',
            description: `Task #${taskId} submitted to session #${sessionId}`,
            data: log.args,
            blockNumber: Number(log.blockNumber),
            transactionHash: log.transactionHash,
            sessionId,
            taskId
          })
        }
      })
    },
  })

  // Watch for task assigned events
  useWatchSessionQueueV2TaskAssignedEvent({
    enabled: isWatchingEnabled,
    onLogs(logs) {
      logs.forEach((log) => {
        if (log.args.sessionId && log.args.taskId) {
          const sessionId = Number(log.args.sessionId)
          const taskId = Number(log.args.taskId)

          addEvent({
            type: 'task_assigned',
            title: 'Task Assigned',
            description: `Task #${taskId} assigned to miners in session #${sessionId}`,
            data: log.args,
            blockNumber: Number(log.blockNumber),
            transactionHash: log.transactionHash,
            sessionId,
            taskId
          })
        }
      })
    },
  })

  // Watch for task ended events
  // Note: This event watcher is used for real-time UI logging only.
  // The useCortensorTasks hook already handles refetching data when tasks end,
  // and queries have automatic refetch intervals, so this is not redundant.
  useWatchSessionQueueV2TaskEndedEvent({
    enabled: isWatchingEnabled,
    onLogs(logs) {
      logs.forEach((log) => {
        if (log.args.sessionId && log.args.taskId) {
          const sessionId = Number(log.args.sessionId)
          const taskId = Number(log.args.taskId)

          addEvent({
            type: 'task_ended',
            title: 'Task Completed',
            description: `Task #${taskId} completed in session #${sessionId}`,
            data: log.args,
            blockNumber: Number(log.blockNumber),
            transactionHash: log.transactionHash,
            sessionId,
            taskId
          })
        }
      })
    },
  })

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'task_submitted':
        return <Zap className="h-4 w-4 text-primary" />
      case 'task_assigned':
        return <Users className="h-4 w-4 text-secondary" />
      case 'task_ended':
        return <CheckCircle className="h-4 w-4 text-accent" />
      case 'session_created':
        return <Activity className="h-4 w-4 text-primary" />
      default:
        return <Activity className="h-4 w-4 text-muted-foreground" />
    }
  }

  const getEventColor = (type: string) => {
    switch (type) {
      case 'task_submitted':
        return 'bg-card/50 border-border hover:bg-card/70'
      case 'task_assigned':
        return 'bg-card/50 border-border hover:bg-card/70'
      case 'task_ended':
        return 'bg-card/50 border-border hover:bg-card/70'
      case 'session_created':
        return 'bg-card/50 border-border hover:bg-card/70'
      default:
        return 'bg-card/50 border-border hover:bg-card/70'
    }
  }

  const EventCard = ({ event }: { event: BlockchainEvent }) => (
    <Card className={cn('mb-2 transition-all duration-200 hover:shadow-md', getEventColor(event.type))}>
      <CardContent className="p-2 sm:p-3">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-1 sm:gap-2 flex-1 min-w-0">
            <div className="flex-shrink-0">{getEventIcon(event.type)}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1 sm:gap-2 mb-1">
                <h4 className="text-xs sm:text-sm font-medium text-card-foreground truncate">{event.title}</h4>
                <Badge variant="outline" className="text-xs px-1 py-0 border-border text-muted-foreground hidden sm:inline-flex">
                  {event.type.replace('_', ' ')}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground mb-2 line-clamp-2">
                {event.description}
              </p>

              <div className="flex items-center gap-2 sm:gap-3 text-xs text-muted-foreground flex-wrap">
                <div className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  <span className="hidden sm:inline">{event.timestamp.toLocaleTimeString()}</span>
                  <span className="sm:hidden">{event.timestamp.toLocaleTimeString().slice(0, 5)}</span>
                </div>

                {event.blockNumber && (
                  <div className="flex items-center gap-1">
                    <Hash className="h-3 w-3" />
                    <span className="hidden sm:inline">Block {event.blockNumber}</span>
                    <span className="sm:hidden">#{event.blockNumber}</span>
                  </div>
                )}

                {event.sessionId && (
                  <Badge variant="secondary" className="text-xs px-1 py-0 bg-muted text-muted-foreground">
                    S#{event.sessionId}
                  </Badge>
                )}

                {event.taskId && (
                  <Badge variant="secondary" className="text-xs px-1 py-0 bg-muted text-muted-foreground">
                    T#{event.taskId}
                  </Badge>
                )}
              </div>

              {event.transactionHash && (
                <div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
                  <ExternalLink className="h-3 w-3" />
                  <span className="font-mono truncate">
                    {event.transactionHash.slice(0, 8)}...{event.transactionHash.slice(-6)}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )

  // Filter events for current session if one is selected
  const filteredEvents = currentSessionId
    ? events.filter(event => !event.sessionId || event.sessionId === currentSessionId)
    : events

  return (
    <div className={cn('h-full flex flex-col', className)}>
      <Collapsible open={isOpen} onOpenChange={setIsOpen} className="h-full flex flex-col">
        <CollapsibleTrigger asChild>
          <Card className="cursor-pointer hover:bg-card/70 transition-colors bg-card border-border flex-shrink-0">
            <CardHeader className="pb-2 p-3 sm:p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1 sm:gap-2 min-w-0 flex-1">
                  <Activity className="h-4 w-4 sm:h-5 sm:w-5" />
                  <CardTitle className="text-sm sm:text-lg truncate">
                    <span className="hidden sm:inline">Event Logger</span>
                    <span className="sm:hidden">Events</span>
                  </CardTitle>
                  {filteredEvents.length > 0 && (
                    <Badge variant="secondary" className="text-xs px-1 py-0">
                      {filteredEvents.length}
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
                  {events.length > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        clearEvents()
                      }}
                      className="h-7 w-7 sm:h-8 sm:w-8 p-0"
                    >
                      <Trash2 className="h-3 w-3 sm:h-4 sm:w-4" />
                    </Button>
                  )}
                  {isOpen ?
                    <ChevronDown className="h-3 w-3 sm:h-4 sm:w-4" /> :
                    <ChevronRight className="h-3 w-3 sm:h-4 sm:w-4" />
                  }
                </div>
              </div>
              <CardDescription className="text-xs sm:text-sm truncate">
                <span className="hidden sm:inline">Real-time blockchain events and activity logs</span>
                <span className="sm:hidden">Real-time blockchain events</span>
                {currentSessionId && ` (S#${currentSessionId})`}
              </CardDescription>
            </CardHeader>
          </Card>
        </CollapsibleTrigger>

        <CollapsibleContent className="flex-1 flex flex-col min-h-0">
          <Card className="bg-card border-border h-full flex flex-col">
            <CardContent className="p-3 sm:p-4 flex-1 flex flex-col min-h-0">
              {filteredEvents.length === 0 ? (
                <div className="text-center py-4 sm:py-8 text-muted-foreground flex-1 flex items-center justify-center">
                  <div>
                    <Activity className="h-6 w-6 sm:h-8 sm:w-8 mx-auto mb-2 opacity-50 text-muted-foreground" />
                    <p className="text-xs sm:text-sm text-muted-foreground">No events yet</p>
                    <p className="text-xs text-muted-foreground/70 hidden sm:block">Blockchain events will appear here in real-time</p>
                  </div>
                </div>
              ) : (
                <ScrollArea className="flex-1">
                  <div className="space-y-2 pr-2">
                    {filteredEvents.map(event => (
                      <EventCard key={event.id} event={event} />
                    ))}
                  </div>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </CollapsibleContent>
      </Collapsible>
    </div>
  )
}