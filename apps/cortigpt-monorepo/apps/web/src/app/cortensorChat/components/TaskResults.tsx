'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Textarea } from '@/components/ui/textarea'
import {
  CheckCircle,
  Clock,
  Users,
  Copy,
  Eye,
  EyeOff,
  RefreshCw,
  AlertCircle,
  Zap
} from 'lucide-react'
import { useCortensorTasks, type TaskData } from '../hooks/useCortensorTasks'
import { useCortensorSession } from '../hooks/useCortensorSession'
import { formatDistanceToNow } from 'date-fns'
import { toast } from 'sonner'

interface TaskResultsProps {
  className?: string
}

export function TaskResults({ className }: TaskResultsProps) {
  const { tasks } = useCortensorTasks()
  const { currentSession } = useCortensorSession()
  const [isVisible, setIsVisible] = useState(true)
  const [selectedTask, setSelectedTask] = useState<TaskData | null>(null)
  const [expandedResults, setExpandedResults] = useState<Set<number>>(new Set())

  // Filter tasks for current session and sort by timestamp
  const sessionTasks = tasks
    .filter(task => !currentSession || task.sessionId === currentSession.sessionId)
    .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())

  const completedTasks = sessionTasks.filter(task => task.status === 'completed')
  const activeTasks = sessionTasks.filter(task => task.status !== 'completed' && task.status !== 'failed')
  const failedTasks = sessionTasks.filter(task => task.status === 'failed')

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      toast.success('Copied to clipboard')
    } catch (error) {
      toast.error('Failed to copy to clipboard')
    }
  }

  const toggleResultExpansion = (taskId: number) => {
    setExpandedResults(prev => {
      const newSet = new Set(prev)
      if (newSet.has(taskId)) {
        newSet.delete(taskId)
      } else {
        newSet.add(taskId)
      }
      return newSet
    })
  }

  const getStatusIcon = (status: TaskData['status']) => {
    switch (status) {
      case 'submitting':
        return <RefreshCw className="h-4 w-4 animate-spin text-blue-500" />
      case 'queued':
        return <Clock className="h-4 w-4 text-yellow-500" />
      case 'assigned':
        return <Users className="h-4 w-4 text-orange-500" />
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      default:
        return null
    }
  }

  const getStatusBadgeVariant = (status: TaskData['status']) => {
    switch (status) {
      case 'completed':
        return 'default'
      case 'failed':
        return 'destructive'
      case 'assigned':
        return 'secondary'
      default:
        return 'outline'
    }
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
          Show Task Results
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
              <Zap className="h-5 w-5" />
              <CardTitle className="text-lg">Task Results</CardTitle>
              <Badge variant="outline" className="text-xs">
                {sessionTasks.length} tasks
              </Badge>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsVisible(false)}
            >
              <EyeOff className="h-4 w-4" />
            </Button>
          </div>

          {currentSession && (
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <CheckCircle className="h-3 w-3 text-green-500" />
                {completedTasks.length} completed
              </span>
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3 text-yellow-500" />
                {activeTasks.length} active
              </span>
              {failedTasks.length > 0 && (
                <span className="flex items-center gap-1">
                  <AlertCircle className="h-3 w-3 text-red-500" />
                  {failedTasks.length} failed
                </span>
              )}
            </div>
          )}
        </CardHeader>

        <CardContent>
          {sessionTasks.length === 0 ? (
            <div className="text-center py-8">
              <Zap className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">
                {currentSession
                  ? 'No tasks found for this session. Submit a message to create your first task.'
                  : 'Select a session to view its tasks and results.'
                }
              </p>
            </div>
          ) : (
            <ScrollArea className="h-[500px]">
              <div className="space-y-4">
                {sessionTasks.map((task) => (
                  <div key={`${task.sessionId}-${task.taskId}`} className="border rounded-lg p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(task.status)}
                        <Badge
                          variant={getStatusBadgeVariant(task.status)}
                          className="text-xs"
                        >
                          {task.status}
                        </Badge>
                        <span className="text-sm font-medium">
                          Task #{task.taskId}
                        </span>
                        {task.globalId && (
                          <span className="text-xs text-muted-foreground">
                            (Global: {task.globalId})
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">
                          {formatDistanceToNow(task.timestamp, { addSuffix: true })}
                        </span>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => copyToClipboard(task.content)}
                        >
                          <Copy className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>

                    {/* Task Content */}
                    <div className="mb-3">
                      <h4 className="text-sm font-medium mb-1">User Message:</h4>
                      <p className="text-sm bg-muted p-2 rounded text-muted-foreground">
                        {task.content}
                      </p>
                    </div>

                    {/* Task Details */}
                    <div className="grid grid-cols-2 gap-4 mb-3 text-xs">
                      <div>
                        <span className="font-medium">Session ID:</span>
                        <span className="ml-2 text-muted-foreground">{task.sessionId}</span>
                      </div>
                      <div>
                        <span className="font-medium">Status:</span>
                        <span className="ml-2 text-muted-foreground capitalize">{task.status}</span>
                      </div>
                      {task.assignedMiners && task.assignedMiners.length > 0 && (
                        <div className="col-span-2">
                          <span className="font-medium">Assigned Miners:</span>
                          <span className="ml-2 text-muted-foreground">
                            {task.assignedMiners.length} miners
                          </span>
                        </div>
                      )}
                    </div>

                    {/* AI Results */}
                    {task.status === 'completed' && task.results && task.results.length > 0 && (
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="text-sm font-medium">AI Response:</h4>
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="text-xs">
                              {task.results.length} result(s)
                            </Badge>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => toggleResultExpansion(task.taskId)}
                            >
                              {expandedResults.has(task.taskId) ? (
                                <EyeOff className="h-3 w-3" />
                              ) : (
                                <Eye className="h-3 w-3" />
                              )}
                            </Button>
                          </div>
                        </div>

                        {task.results.map((result, index) => (
                          <div key={index} className="mb-2">
                            {task.results!.length > 1 && (
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-xs font-medium">Result {index + 1}:</span>
                                {task.resultMiners && task.resultMiners[index] && (
                                  <span className="text-xs text-muted-foreground font-mono">
                                    {task.resultMiners[index].slice(0, 8)}...
                                  </span>
                                )}
                              </div>
                            )}

                            {expandedResults.has(task.taskId) ? (
                              <Textarea
                                value={result}
                                readOnly
                                className="min-h-[100px] text-sm"
                              />
                            ) : (
                              <div className="bg-muted p-3 rounded text-sm">
                                <p className="line-clamp-3">{result}</p>
                                {result.length > 150 && (
                                  <Button
                                    variant="link"
                                    size="sm"
                                    className="p-0 h-auto text-xs mt-1"
                                    onClick={() => toggleResultExpansion(task.taskId)}
                                  >
                                    Show more...
                                  </Button>
                                )}
                              </div>
                            )}

                            <div className="flex items-center gap-2 mt-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => copyToClipboard(result)}
                              >
                                <Copy className="h-3 w-3 mr-1" />
                                Copy Response
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Processing Status */}
                    {task.status === 'assigned' && (
                      <div className="bg-orange-50 dark:bg-orange-950/20 p-3 rounded text-sm">
                        <div className="flex items-center gap-2 text-orange-700 dark:text-orange-300">
                          <Users className="h-4 w-4" />
                          <span className="font-medium">Processing in progress...</span>
                        </div>
                        <p className="text-orange-600 dark:text-orange-400 mt-1">
                          Task is being processed by {task.assignedMiners?.length || 0} miners.
                        </p>
                      </div>
                    )}

                    {task.status === 'failed' && (
                      <div className="bg-red-50 dark:bg-red-950/20 p-3 rounded text-sm">
                        <div className="flex items-center gap-2 text-red-700 dark:text-red-300">
                          <AlertCircle className="h-4 w-4" />
                          <span className="font-medium">Task failed</span>
                        </div>
                        <p className="text-red-600 dark:text-red-400 mt-1">
                          This task failed to complete. You may try submitting it again.
                        </p>
                      </div>
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