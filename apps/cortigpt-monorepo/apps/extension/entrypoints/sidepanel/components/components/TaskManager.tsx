'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
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
  Clock,
  CheckCircle,
  XCircle,
  Users,
  MessageSquare,
  Zap,
  Hash,
  Calendar,
  Server,
  Type,
  Mail
} from 'lucide-react'
import { useCortensorTasks } from '../hooks/useCortensorTasks'
import { useCurrentSession } from '../store/useSessionStore'
import { cn } from '@/lib/utils'

interface TaskManagerProps {
  className?: string
}

export function TaskManager({ className }: TaskManagerProps) {
  const { tasks, isSubmittingTask } = useCortensorTasks()
  const currentSession = useCurrentSession()
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    overview: true,
    active: true,
    completed: false,
    failed: false
  })

  const toggleSection = (section: string) => {
    setOpenSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }))
  }

  // Function to parse and render task content
  const renderTaskContent = (content: string) => {
    try {
      const parsed = JSON.parse(content)
      
      if (parsed.type === 'chat' && parsed.message) {
        return (
          <div className="space-y-2">
            <div className="flex items-center gap-2 p-2 bg-blue-50 dark:bg-blue-950/30 rounded border border-blue-200 dark:border-blue-800">
              <Mail className="h-3 w-3 text-blue-600 dark:text-blue-400" />
              <span className="text-xs font-medium text-blue-700 dark:text-blue-300">Chat Message</span>
            </div>
            <div className="p-3 bg-background rounded border">
              <p className="text-sm text-card-foreground leading-relaxed">
                {parsed.message}
              </p>
            </div>
          </div>
        )
      }
      
      // For other JSON structures, render as formatted JSON
      return (
        <div className="space-y-2">
          <div className="flex items-center gap-2 p-2 bg-amber-50 dark:bg-amber-950/30 rounded border border-amber-200 dark:border-amber-800">
            <Type className="h-3 w-3 text-amber-600 dark:text-amber-400" />
            <span className="text-xs font-medium text-amber-700 dark:text-amber-300">Structured Data</span>
          </div>
          <div className="p-3 bg-background rounded border font-mono text-xs">
            <pre className="whitespace-pre-wrap break-words text-muted-foreground">
              {JSON.stringify(parsed, null, 2)}
            </pre>
          </div>
        </div>
      )
    } catch (error) {
      // If not valid JSON, render as plain text
      return (
        <div className="p-3 bg-background rounded border">
          <p className="text-sm text-card-foreground leading-relaxed whitespace-pre-wrap break-words">
            {content}
          </p>
        </div>
      )
    }
  }

  const activeTasks = tasks.filter(task =>
    task.status === 'queued' || task.status === 'assigned'
  )
  const completedTasks = tasks.filter(task => task.status === 'completed')
  const failedTasks = tasks.filter(task => task.status === 'failed')
  const submittingTasks = tasks.filter(task => task.status === 'submitting')

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'submitting':
        return <Clock className="w-4 h-4 animate-pulse text-secondary" />
      case 'queued':
        return <Activity className="w-4 h-4 text-primary" />
      case 'assigned':
        return <Users className="w-4 h-4 text-accent" />
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-primary" />
      case 'failed':
        return <XCircle className="w-4 h-4 text-destructive" />
      default:
        return <Activity className="w-4 h-4 text-muted-foreground" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'submitting':
        return 'bg-secondary/20 text-secondary border-secondary/30'
      case 'queued':
        return 'bg-primary/20 text-primary border-primary/30'
      case 'assigned':
        return 'bg-accent/20 text-accent border-accent/30'
      case 'completed':
        return 'bg-primary/20 text-primary border-primary/30'
      case 'failed':
        return 'bg-destructive/20 text-destructive border-destructive/30'
      default:
        return 'bg-muted text-muted-foreground border-border'
    }
  }

  const TaskCard = ({ task }: { task: any }) => (
    <Card className="mb-3 transition-all duration-200 bg-card border-border hover:shadow-md hover:border-primary/30">
      <CardHeader className="p-3 pb-3 sm:p-4">
        <div className="flex gap-2 justify-between items-start">
          <div className="flex flex-1 gap-2 items-center min-w-0">
            <div className="flex-shrink-0">{getStatusIcon(task.status)}</div>
            <div className="flex-1 min-w-0">
              <div className="flex gap-2 items-center mb-1">
                <CardTitle className="text-sm font-semibold sm:text-base text-card-foreground">
                  Task #{task.taskId}
                </CardTitle>
                <Badge className={cn('text-xs px-2 py-1 font-medium', getStatusColor(task.status))}>
                  {task.status.charAt(0).toUpperCase() + task.status.slice(1)}
                </Badge>
              </div>
              <div className="flex gap-2 items-center text-xs text-muted-foreground">
                <Calendar className="w-3 h-3" />
                <span className="hidden sm:inline">{task.timestamp.toLocaleString()}</span>
                <span className="sm:hidden">{task.timestamp.toLocaleDateString()} {task.timestamp.toLocaleTimeString().slice(0, 5)}</span>
                {task.globalId && (
                  <>
                    <span className="text-muted-foreground/50">•</span>
                    <Hash className="w-3 h-3" />
                    <span>ID: {task.globalId}</span>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-3 pt-0 sm:p-4">
        <div className="space-y-3 sm:space-y-4">
          {/* Task Content */}
          <div className="p-3 rounded-lg border bg-muted/50 border-muted">
            <p className="flex gap-1 items-center mb-3 text-xs font-medium sm:text-sm text-card-foreground">
              <MessageSquare className="w-3 h-3" />
              Task Content
            </p>
            <div className="overflow-y-auto max-h-40">
              {renderTaskContent(task.content)}
            </div>
          </div>

          {/* Miners Section */}
          {task.assignedMiners && task.assignedMiners.length > 0 && (
            <div className="p-3 rounded-lg border bg-accent/5 border-accent/20">
              <div className="flex justify-between items-center mb-2">
                <p className="flex gap-1 items-center text-xs font-medium sm:text-sm text-card-foreground">
                  <Server className="w-3 h-3" />
                  Assigned Miners
                </p>
                <Badge variant="outline" className="px-2 py-0 text-xs">
                  {task.assignedMiners.length} miners
                </Badge>
              </div>
              <div className="overflow-y-auto max-h-32">
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {task.assignedMiners.map((miner: string, index: number) => (
                    <div key={index} className="p-2 font-mono text-xs rounded border transition-colors bg-background text-muted-foreground hover:bg-muted/50">
                      <div className="truncate" title={miner}>
                        {miner.slice(0, 10)}...{miner.slice(-8)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Results Section */}
          {task.results && task.results.length > 0 && (
            <div className="p-3 rounded-lg border bg-primary/5 border-primary/20">
              <div className="flex justify-between items-center mb-2">
                <p className="flex gap-1 items-center text-xs font-medium sm:text-sm text-card-foreground">
                  <CheckCircle className="w-3 h-3 text-primary" />
                  AI Results
                </p>
                <Badge variant="outline" className="px-2 py-0 text-xs">
                  {task.results.length} results
                </Badge>
              </div>
              <div className="overflow-y-auto space-y-2 max-h-40">
                {task.results.map((result: string, index: number) => (
                  <div key={index} className="p-3 text-xs leading-relaxed rounded border transition-colors sm:text-sm bg-background border-primary/30 text-card-foreground hover:bg-primary/5">
                    <div className="overflow-y-auto max-h-24">
                      <p className="whitespace-pre-wrap break-words">{result}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Transaction Hash */}
          {task.transactionHash && (
            <div className="flex gap-2 items-center p-2 text-xs rounded border text-muted-foreground bg-muted/30">
              <Hash className="w-3 h-3" />
              <span className="font-medium">Transaction:</span>
              <span className="flex-1 font-mono truncate">
                {task.transactionHash.slice(0, 12)}...{task.transactionHash.slice(-10)}
              </span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )

  if (!currentSession) {
    return (
      <Card className={`flex flex-col h-full ${className}`}>
        <CardHeader className="p-3 sm:p-4">
          <CardTitle className="flex gap-2 items-center text-sm sm:text-lg">
            <Activity className="w-4 h-4 sm:h-5 sm:w-5" />
            Tasks
          </CardTitle>
          <CardDescription className="text-xs sm:text-sm">
            No active session. Please select a session.
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <div className={cn('flex flex-col space-y-2 h-full sm:space-y-3', className)}>
      {/* Overview Section */}
      <Collapsible
        open={openSections.overview}
        onOpenChange={() => toggleSection('overview')}
        className="flex-shrink-0"
      >
        <CollapsibleTrigger asChild>
          <Card className="transition-colors cursor-pointer hover:bg-card/70 bg-card border-border">
            <CardHeader className="p-3 sm:p-4">
              <div className="flex justify-between items-center">
                <CardTitle className="flex gap-2 items-center text-sm text-card-foreground sm:text-base">
                  <Activity className="w-4 h-4 sm:h-5 sm:w-5 text-primary" />
                  <span className="hidden sm:inline">Task Overview</span>
                  <span className="sm:hidden">Tasks</span>
                </CardTitle>
                {openSections.overview ?
                  <ChevronDown className="w-3 h-3 sm:h-4 sm:w-4" /> :
                  <ChevronRight className="w-3 h-3 sm:h-4 sm:w-4" />
                }
              </div>
            </CardHeader>
          </Card>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <Card className="bg-card border-border">
            <CardContent className="p-3 pt-3 sm:pt-6 sm:p-6">
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 sm:gap-4">
                <div className="text-center">
                  <div className="text-lg font-bold sm:text-2xl text-primary">{activeTasks.length}</div>
                  <div className="text-xs sm:text-sm text-muted-foreground">Active</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold sm:text-2xl text-accent">{completedTasks.length}</div>
                  <div className="text-xs sm:text-sm text-muted-foreground">Done</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold sm:text-2xl text-destructive">{failedTasks.length}</div>
                  <div className="text-xs sm:text-sm text-muted-foreground">Failed</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold sm:text-2xl text-secondary">{submittingTasks.length}</div>
                  <div className="text-xs sm:text-sm text-muted-foreground">Pending</div>
                </div>
              </div>

              {isSubmittingTask && (
                <div className="p-2 mt-3 rounded-lg border sm:mt-4 sm:p-3 bg-secondary/20 border-secondary/30">
                  <div className="flex gap-2 items-center text-secondary">
                    <Zap className="w-3 h-3 animate-pulse sm:h-4 sm:w-4" />
                    <span className="text-xs font-medium sm:text-sm">Submitting new task...</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </CollapsibleContent>
      </Collapsible>

      {/* Active Tasks */}
      {activeTasks.length > 0 && (
        <Collapsible
          open={openSections.active}
          onOpenChange={() => toggleSection('active')}
          className="flex-shrink-0"
        >
          <CollapsibleTrigger asChild>
            <Card className="transition-colors cursor-pointer hover:bg-card/70 bg-card border-border hover:border-primary/30">
              <CardHeader className="p-3 sm:p-4">
                <div className="flex justify-between items-center">
                  <CardTitle className="flex gap-2 items-center text-sm text-card-foreground sm:text-base">
                    <Activity className="w-4 h-4 animate-pulse sm:h-5 sm:w-5 text-primary" />
                    <span className="hidden sm:inline">Active Tasks</span>
                    <span className="sm:hidden">Active</span>
                    <Badge variant="secondary" className="px-2 py-1 text-xs bg-primary/10 text-primary border-primary/20">
                      {activeTasks.length}
                    </Badge>
                  </CardTitle>
                  {openSections.active ?
                    <ChevronDown className="w-3 h-3 sm:h-4 sm:w-4 text-primary" /> :
                    <ChevronRight className="w-3 h-3 sm:h-4 sm:w-4 text-primary" />
                  }
                </div>
                <CardDescription className="text-xs sm:text-sm text-muted-foreground">
                  Tasks currently being processed by miners
                </CardDescription>
              </CardHeader>
            </Card>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <ScrollArea className="h-[400px] sm:h-[500px] lg:h-[600px]">
              <div className="pr-3 space-y-3">
                {activeTasks.map(task => (
                  <TaskCard key={`${task.sessionId}-${task.taskId}`} task={task} />
                ))}
              </div>
            </ScrollArea>
          </CollapsibleContent>
        </Collapsible>
      )}

      {/* Completed Tasks */}
      {completedTasks.length > 0 && (
        <Collapsible
          open={openSections.completed}
          onOpenChange={() => toggleSection('completed')}
          className="flex-shrink-0"
        >
          <CollapsibleTrigger asChild>
            <Card className="transition-colors cursor-pointer hover:bg-card/70 bg-card border-border">
              <CardHeader className="p-3 sm:p-4">
                <div className="flex justify-between items-center">
                  <CardTitle className="flex gap-2 items-center text-sm text-card-foreground sm:text-base">
                    <CheckCircle className="w-4 h-4 sm:h-5 sm:w-5 text-accent" />
                    <span className="hidden sm:inline">Completed Tasks ({completedTasks.length})</span>
                    <span className="sm:hidden">Done ({completedTasks.length})</span>
                  </CardTitle>
                  {openSections.completed ?
                    <ChevronDown className="w-3 h-3 sm:h-4 sm:w-4" /> :
                    <ChevronRight className="w-3 h-3 sm:h-4 sm:w-4" />
                  }
                </div>
              </CardHeader>
            </Card>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <ScrollArea className="h-[300px] sm:h-[400px] lg:h-[500px]">
              <div className="pr-2 space-y-2">
                {completedTasks.map(task => (
                  <TaskCard key={`${task.sessionId}-${task.taskId}`} task={task} />
                ))}
              </div>
            </ScrollArea>
          </CollapsibleContent>
        </Collapsible>
      )}

      {/* Failed Tasks */}
      {failedTasks.length > 0 && (
        <Collapsible
          open={openSections.failed}
          onOpenChange={() => toggleSection('failed')}
          className="flex-shrink-0"
        >
          <CollapsibleTrigger asChild>
            <Card className="transition-colors cursor-pointer hover:bg-card/70 bg-card border-border">
              <CardHeader className="p-3 sm:p-4">
                <div className="flex justify-between items-center">
                  <CardTitle className="flex gap-2 items-center text-sm text-card-foreground sm:text-base">
                    <XCircle className="w-4 h-4 sm:h-5 sm:w-5 text-destructive" />
                    <span className="hidden sm:inline">Failed Tasks ({failedTasks.length})</span>
                    <span className="sm:hidden">Failed ({failedTasks.length})</span>
                  </CardTitle>
                  {openSections.failed ?
                    <ChevronDown className="w-3 h-3 sm:h-4 sm:w-4" /> :
                    <ChevronRight className="w-3 h-3 sm:h-4 sm:w-4" />
                  }
                </div>
              </CardHeader>
            </Card>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <ScrollArea className="h-[300px] sm:h-[400px] lg:h-[500px]">
              <div className="pr-2 space-y-2">
                {failedTasks.map(task => (
                  <TaskCard key={`${task.sessionId}-${task.taskId}`} task={task} />
                ))}
              </div>
            </ScrollArea>
          </CollapsibleContent>
        </Collapsible>
      )}
    </div>
  )
}