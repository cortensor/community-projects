'use client'

import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  Send,
  Bot,
  User,
  Loader2,
  Clock,
  CheckCircle,
  AlertCircle,
  Users,
  Zap
} from 'lucide-react'
import { useCortensorTasks, type ChatMessage, type TaskData } from '../hooks/useCortensorTasks'
import { useCurrentSession, useSessionStore } from '../store/useSessionStore'
import { formatDistanceToNow } from 'date-fns'
import { toast } from 'sonner'

interface ChatInterfaceProps {
  className?: string
}

export function ChatInterface({ className }: ChatInterfaceProps) {
  const currentSession = useCurrentSession()
  const { setSessionDialogOpen } = useSessionStore()
  const {
    messages,
    tasks,
    isSubmittingTask,
    submitTask
  } = useCortensorTasks()

  const [currentMessage, setCurrentMessage] = useState('')

  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]')
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight
      }
    }
  }, [messages])

  // Focus input when session changes
  useEffect(() => {
    if (currentSession && inputRef.current) {
      inputRef.current.focus()
    }
  }, [currentSession])

  const handleSendMessage = async () => {
    if (!currentMessage.trim()) return

    if (!currentSession) {
      toast.error('Please select or create a session first')
      setSessionDialogOpen(true)
      return
    }

    const messageToSend = currentMessage.trim()
    setCurrentMessage('')

    try {
      await submitTask(currentSession.sessionId, messageToSend)
    } catch (error) {
      console.error('Failed to send message:', error)
      setCurrentMessage(messageToSend) // Restore message on error
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const getTaskStatusIcon = (task: TaskData) => {
    switch (task.status) {
      case 'submitting':
        return <Loader2 className="w-3 h-3 text-blue-500 animate-spin" />
      case 'queued':
        return <Clock className="w-3 h-3 text-yellow-500" />
      case 'assigned':
        return <Users className="w-3 h-3 text-orange-500" />
      case 'completed':
        return <CheckCircle className="w-3 h-3 text-green-500" />
      case 'failed':
        return <AlertCircle className="w-3 h-3 text-red-500" />
      default:
        return null
    }
  }

  const getTaskStatusText = (task: TaskData) => {
    switch (task.status) {
      case 'submitting':
        return 'Submitting...'
      case 'queued':
        return 'Queued'
      case 'assigned':
        return `Assigned to ${task.assignedMiners?.length || 0} miners`
      case 'completed':
        return 'Completed'
      case 'failed':
        return 'Failed'
      default:
        return 'Unknown'
    }
  }

  const getMessageTask = (message: ChatMessage): TaskData | undefined => {
    return tasks.find(task =>
      task.sessionId === message.sessionId && task.taskId === message.taskId
    )
  }

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header - Compact for mobile */}
      <div className="flex-shrink-0 p-0 border-b bg-card sm:p-4">
        <div className="flex justify-between items-center">
          <div className="flex gap-2 items-center">
            <div className="flex justify-center items-center w-6 h-6 rounded-full sm:w-8 sm:h-8 bg-primary/10">
              <Bot className="w-3 h-3 sm:h-4 sm:w-4 text-primary" />
            </div>
            <div>
              <h1 className="text-sm font-semibold sm:text-lg">Chat</h1>
              {currentSession && (
                <div className="flex gap-1 items-center sm:gap-2">
                  <Badge variant="outline" className="px-1 py-0 text-xs">
                    #{currentSession.sessionId}
                  </Badge>
                  <Badge variant="secondary" className="px-1 py-0 text-xs">
                    {messages.length}
                  </Badge>
                </div>
              )}
            </div>
          </div>

          {/* Session info - hidden on small screens */}
          {currentSession && (
            <div className="hidden gap-3 items-center text-xs md:flex text-muted-foreground">
              <span className="flex gap-1 items-center">
                <Users className="w-3 h-3" />
                {currentSession.nodeCount}
              </span>
              <span className="flex gap-1 items-center">
                <Zap className="w-3 h-3" />
                {currentSession.redundant}x
              </span>
              <span className="flex gap-1 items-center">
                <Clock className="w-3 h-3" />
                {currentSession.sla}ms
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Messages Area - Takes remaining space */}
      <div className="flex flex-col flex-1 min-h-0">
        {!currentSession ? (
          <div className="flex flex-1 justify-center items-center p-4 sm:p-6">
            <div className="text-center">
              <Bot className="mx-auto mb-2 w-8 h-8 sm:h-12 sm:w-12 text-muted-foreground sm:mb-4" />
              <h3 className="mb-2 text-base font-medium sm:text-lg">No Active Session</h3>
              <p className="mb-4 text-xs sm:text-sm text-muted-foreground">
                Select an existing session or create a new one to start chatting.
              </p>
              <Button onClick={() => setSessionDialogOpen(true)} size="sm">
                Create New Session
              </Button>
            </div>
          </div>
        ) : (
          <>
            {/* Scrollable Messages */}
            <ScrollArea className="flex-1 px-1 sm:px-4" ref={scrollAreaRef}>
              {messages.length === 0 ? (
                <div className="flex items-center justify-center h-full min-h-[200px]">
                  <div className="text-center">
                    <Bot className="mx-auto mb-2 w-6 h-6 sm:h-8 sm:w-8 text-muted-foreground" />
                    <p className="text-xs sm:text-sm text-muted-foreground">
                      Start a conversation by typing a message below.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="py-3 space-y-3 sm:space-y-4 sm:py-4">
                  {messages.map((message) => {
                    const task = getMessageTask(message)

                    return (
                      <div
                        key={message.id}
                        className={`flex gap-2 sm:gap-3 ${message.sender === 'user' ? 'justify-end' : 'justify-start'
                          }`}
                      >
                        {message.sender === 'ai' && (
                          <div className="flex-shrink-0">
                            <div className="flex justify-center items-center w-6 h-6 rounded-full sm:w-8 sm:h-8 bg-primary/10">
                              <Bot className="w-3 h-3 sm:h-4 sm:w-4 text-primary" />
                            </div>
                          </div>
                        )}

                        <div className={`max-w-[85%] sm:max-w-[80%] ${message.sender === 'user' ? 'order-first' : ''
                          }`}>
                          <div className={`rounded-lg px-3 py-2 sm:px-4 sm:py-2 ${message.sender === 'user'
                            ? 'bg-primary text-primary-foreground ml-auto'
                            : 'bg-muted'
                            }`}>
                            <p className="text-xs whitespace-pre-wrap sm:text-sm">{message.content}</p>
                          </div>

                          <div className={`flex items-center gap-1 sm:gap-2 mt-1 text-xs text-muted-foreground ${message.sender === 'user' ? 'justify-end' : 'justify-start'
                            }`}>
                            <span className="text-xs">
                              {formatDistanceToNow(message.timestamp, { addSuffix: true })}
                            </span>

                            {task && message.sender === 'user' && (
                              <>
                                <Separator orientation="vertical" className="h-3" />
                                <div className="flex gap-1 items-center">
                                  {getTaskStatusIcon(task)}
                                  <span className="hidden sm:inline">{getTaskStatusText(task)}</span>
                                </div>
                                {task.taskId && (
                                  <>
                                    <Separator orientation="vertical" className="h-3" />
                                    <span className="text-xs">#{task.taskId}</span>
                                  </>
                                )}
                              </>
                            )}
                          </div>
                        </div>

                        {message.sender === 'user' && (
                          <div className="flex-shrink-0">
                            <div className="flex justify-center items-center w-6 h-6 rounded-full sm:w-8 sm:h-8 bg-primary/10">
                              <User className="w-3 h-3 sm:h-4 sm:w-4 text-primary" />
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </ScrollArea>

            {/* Fixed Input Area at Bottom */}
            <div className="flex-shrink-0 p-1 border-t bg-background sm:p-4">
              <div className="flex gap-2">
                <Input
                  ref={inputRef}
                  placeholder="Type your message..."
                  value={currentMessage}
                  onChange={(e) => setCurrentMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  disabled={isSubmittingTask}
                  className="flex-1 text-sm"
                />
                <Button
                  onClick={handleSendMessage}
                  disabled={!currentMessage.trim() || isSubmittingTask}
                  size="sm"
                  className="px-3"
                >
                  {isSubmittingTask ? (
                    <Loader2 className="w-3 h-3 animate-spin sm:h-4 sm:w-4" />
                  ) : (
                    <Send className="w-3 h-3 sm:h-4 sm:w-4" />
                  )}
                </Button>
              </div>

              {isSubmittingTask && (
                <div className="flex gap-2 items-center mt-2 text-xs text-muted-foreground">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  <span>Submitting task...</span>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}