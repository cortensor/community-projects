'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  ChevronDown,
  Plus,
  RefreshCw,
  Settings,
  Calendar,
  Users,
  Clock,
  Zap
} from 'lucide-react'
import { useCortensorSession } from '../hooks/useCortensorSession'
import { useChatStore } from '../store/useChatStore'
import { SessionCreationDialog } from './SessionCreationDialog'
import { formatDistanceToNow } from 'date-fns'

interface SessionManagerProps {
  className?: string
}

export function SessionManager({ className }: SessionManagerProps) {
  const {
    currentSession,
    userSessions,
    isLoadingSessions,
    selectSession,
    refreshSessions
  } = useCortensorSession()

  const {
    isSessionDialogOpen,
    setSessionDialogOpen,
    selectedSessionId,
    setSelectedSessionId
  } = useChatStore()

  const [isRefreshing, setIsRefreshing] = useState(false)

  const handleRefresh = async () => {
    setIsRefreshing(true)
    await refreshSessions()
    setIsRefreshing(false)
  }

  const handleSessionSelect = (sessionId: number) => {
    setSelectedSessionId(sessionId)
    selectSession(sessionId)
  }

  const getSessionStatusBadge = (session: any) => {
    const now = Date.now()
    const sessionTime = Number(session.timestamp) * 1000
    const isRecent = now - sessionTime < 24 * 60 * 60 * 1000 // 24 hours

    if (isRecent) {
      return <Badge variant="default" className="text-xs">Active</Badge>
    }
    return <Badge variant="secondary" className="text-xs">Inactive</Badge>
  }

  return (
    <div className={`${className} h-full flex flex-col`}>
      <Card className="h-full flex flex-col">
        <CardHeader className="pb-2 p-3 sm:p-4 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="min-w-0 flex-1">
              <CardTitle className="text-sm sm:text-lg truncate">Sessions</CardTitle>
              <CardDescription className="text-xs sm:text-sm truncate">
                {currentSession
                  ? `Active: ${currentSession.name || `#${currentSession.sessionId}`}`
                  : 'No active session'
                }
              </CardDescription>
            </div>
            <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefresh}
                disabled={isRefreshing || isLoadingSessions}
                className="h-7 w-7 sm:h-8 sm:w-8 p-0"
              >
                <RefreshCw className={`h-3 w-3 sm:h-4 sm:w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              </Button>
              <Button
                size="sm"
                onClick={() => setSessionDialogOpen(true)}
                className="h-7 px-2 sm:h-8 sm:px-3"
              >
                <Plus className="h-3 w-3 sm:h-4 sm:w-4 sm:mr-2" />
                <span className="hidden sm:inline">New</span>
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="flex-1 flex flex-col p-3 sm:p-4 pt-0 min-h-0">
          {currentSession && (
            <>
              <div className="mb-3 flex-shrink-0">
                <h4 className="text-xs sm:text-sm font-medium mb-2">Current Session</h4>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex items-center gap-1">
                    <Users className="h-3 w-3 text-muted-foreground" />
                    <span>{currentSession.nodeCount}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Zap className="h-3 w-3 text-muted-foreground" />
                    <span>{currentSession.redundant}x</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3 text-muted-foreground" />
                    <span>{currentSession.sla}ms</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Calendar className="h-3 w-3 text-muted-foreground" />
                    <span className="truncate">
                      {currentSession.timestamp
                        ? formatDistanceToNow(new Date(Number(currentSession.timestamp) * 1000), { addSuffix: true })
                        : 'No time'
                      }
                    </span>
                  </div>
                </div>
              </div>
              <Separator className="mb-3" />
            </>
          )}

          <div className="flex-1 flex flex-col min-h-0">
            <div className="flex items-center justify-between mb-2 flex-shrink-0">
              <h4 className="text-xs sm:text-sm font-medium">Available Sessions</h4>
              <Badge variant="outline" className="text-xs px-1 py-0">
                {userSessions.length}
              </Badge>
            </div>

            {isLoadingSessions ? (
              <div className="flex items-center justify-center py-4 flex-1">
                <RefreshCw className="h-4 w-4 sm:h-6 sm:w-6 animate-spin text-muted-foreground" />
                <span className="ml-2 text-xs sm:text-sm text-muted-foreground">Loading...</span>
              </div>
            ) : userSessions.length === 0 ? (
              <div className="text-center py-4 flex-1 flex items-center justify-center">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground mb-3">
                    No sessions found. Create your first session.
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSessionDialogOpen(true)}
                    className="h-7 px-2 sm:h-8 sm:px-3"
                  >
                    <Plus className="h-3 w-3 sm:h-4 sm:w-4 sm:mr-2" />
                    <span className="hidden sm:inline">Create</span>
                  </Button>
                </div>
              </div>
            ) : (
              <ScrollArea className="flex-1">
                <div className="space-y-2 pr-2">
                  {userSessions.map((session) => (
                    <div
                      key={session.sessionId}
                      className={`p-2 sm:p-3 rounded-lg border cursor-pointer transition-colors hover:bg-accent ${selectedSessionId === session.sessionId
                        ? 'border-primary bg-accent'
                        : 'border-border'
                        }`}
                      onClick={() => handleSessionSelect(session.sessionId)}
                    >
                      <div className="flex items-center justify-between mb-1 sm:mb-2">
                        <div className="flex items-center gap-1 sm:gap-2 min-w-0 flex-1">
                          <span className="font-medium text-xs sm:text-sm truncate">
                            {session.name || `#${session.sessionId}`}
                          </span>
                          {getSessionStatusBadge(session)}
                        </div>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" className="h-5 w-5 sm:h-6 sm:w-6 p-0 flex-shrink-0">
                              <Settings className="h-2 w-2 sm:h-3 sm:w-3" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={(e) => {
                                e.stopPropagation()
                                handleSessionSelect(session.sessionId)
                              }}
                            >
                              Select Session
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>

                      {session.description && (
                        <p className="text-xs text-muted-foreground mb-1 sm:mb-2 truncate">
                          {session.description}
                        </p>
                      )}

                      <div className="flex items-center gap-2 sm:gap-4 text-xs text-muted-foreground">
                        <span>#{session.sessionId}</span>
                        <span>{session.nodeCount} nodes</span>
                        <span className="truncate">
                          {session.timestamp
                            ? formatDistanceToNow(new Date(Number(session.timestamp) * 1000), { addSuffix: true })
                            : 'No time'
                          }
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
          </div>
        </CardContent>
      </Card>

      <SessionCreationDialog
        open={isSessionDialogOpen}
        onOpenChange={setSessionDialogOpen}
      />
    </div>
  )
}