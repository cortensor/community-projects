// src/components/sliding-panel.tsx
"use client"

import { Button } from "./ui/button"
import { Badge } from "./ui/badge"
import { ScrollArea } from "./ui/scroll-area"
import { PanelLeftOpen, PanelLeftClose, MessageCircle, Plus, Trash2, Bot, X } from "lucide-react"
import { appConfig } from "@/lib/app-config"
import type { ChatSession } from "@/lib/storage"
import type { Environment } from "@/lib/environment-config"
import { cn } from "@/lib/utils"

interface SlidingPanelProps {
  sessions: ChatSession[]
  currentSessionId: string
  onNewSession: () => void
  onLoadSession: (sessionId: string) => void
  onDeleteSession: (sessionId: string) => void
  isOpen: boolean
  onToggle: () => void
  isMobile: boolean
  sortMode?: 'recent' | 'unread'
  onSortChange?: (mode: 'recent' | 'unread') => void
}

export function SlidingPanel({
  sessions,
  currentSessionId,
  onNewSession,
  onLoadSession,
  onDeleteSession,
  isOpen,
  onToggle,
  isMobile,
  sortMode = 'recent',
  onSortChange,
}: SlidingPanelProps) {
  const sessionList = Array.isArray(sessions) ? sessions.slice().reverse() : [];

  const formatTimeAgo = (d?: Date | string) => {
    if (!d) return '';
    const ts = new Date(d).getTime();
    const diff = Date.now() - ts;
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  };

  const estimateTokens = (session: ChatSession) => {
    const text = (session.messages || []).map(m => m.content || '').join(' ');
    const approxTokens = Math.ceil(text.length / 4); // rough heuristic
    if (approxTokens < 1) return '';
    if (approxTokens > 5000) return '>5k tok';
    if (approxTokens > 2000) return '>2k tok';
    if (approxTokens > 1000) return '>1k tok';
    return `${approxTokens} tok`;
  };

  return (
    <>
      <Button
        variant="ghost"
        size="icon"
        onClick={onToggle}
        className={cn(
          "fixed z-[60] bg-background/90 backdrop-blur-md border shadow-lg hover:bg-background/95 transition-all duration-300 ease-in-out border-border/50",
          // Enhanced mobile positioning to avoid header overlap
          isMobile 
            ? "top-16 left-3 h-8 w-8" // Move below header on mobile
            : "top-[4.5rem] left-4 h-10 w-10", // Move below header on desktop too
          // Improve positioning when panel is open to avoid header overlap
          isOpen && !isMobile && "left-[304px]",
        )}
      >
        {isOpen ? <PanelLeftClose className={cn("h-4 w-4", isMobile && "h-3 w-3")} /> : <PanelLeftOpen className={cn("h-4 w-4", isMobile && "h-3 w-3")} />}
      </Button>

      {isMobile && isOpen && <div className="fixed inset-0 bg-black/50 z-40 md:hidden" onClick={onToggle} />}

      <div
        className={cn(
          "fixed left-0 top-0 h-full w-64 bg-background/95 backdrop-blur-md border-r shadow-xl z-40 transition-transform duration-300 ease-in-out",
          !isOpen && "-translate-x-full",
          isMobile && "z-50 w-72",
        )}
      >
        <div className="flex flex-col h-full">
          <div className="p-3 border-b border-border/50">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Bot className="h-5 w-5 text-primary" />
                <div>
                  <h1 className="text-sm font-bold">{appConfig.app.fullName}</h1>
                  <p className="text-xs text-muted-foreground">{appConfig.app.version}</p>
                </div>
              </div>
              {isMobile && (
                <Button variant="ghost" size="icon" onClick={onToggle} className="h-6 w-6">
                  <X className="h-3 w-3" />
                </Button>
              )}
            </div>
            <Button onClick={onNewSession} className="w-full h-8 text-sm shadow-sm" variant="outline">
              <Plus className="h-3 w-3 mr-2" />
              New Chat
            </Button>
          </div>

          <ScrollArea className="flex-1">
            <div className="p-3">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-medium text-muted-foreground">Chat History</h3>
                <Badge variant="secondary" className="text-xs bg-background/50 h-4 px-1.5">
                  {sessionList.length}
                </Badge>
              </div>

              {onSortChange && (
                <div className="flex items-center gap-1 mb-3">
                  <Button size="xs" variant={sortMode === 'recent' ? 'default' : 'ghost'} className="h-7 px-2 text-xs" onClick={() => onSortChange('recent')}>
                    Recent
                  </Button>
                  <Button size="xs" variant={sortMode === 'unread' ? 'default' : 'ghost'} className="h-7 px-2 text-xs" onClick={() => onSortChange('unread')}>
                    Unread
                  </Button>
                </div>
              )}

              <div className="space-y-1">
                {sessionList.map((session) => (
                  <div
                    key={session.id}
                    className={cn(
                      "group relative rounded-md border p-2 cursor-pointer transition-all hover:bg-muted/50 border-border/50 backdrop-blur-sm",
                      "overflow-hidden", // Prevent overflow
                      session.id === currentSessionId
                        ? "bg-primary/10 border-primary/20 shadow-sm"
                        : "bg-background/30",
                    )}
                    onClick={() => {
                      onLoadSession(session.id);
                      if (isMobile) onToggle();
                    }}
                  >
                    <div className="flex items-start gap-2 w-full">
                      <MessageCircle className="h-3 w-3 mt-0.5 flex-shrink-0 text-muted-foreground" />
                      <div className="flex-1 min-w-0 pr-6 max-w-[calc(100%-2rem)]">
                        <div className="flex items-center gap-1 mb-1">
                          <div 
                            className="font-medium text-xs flex-1 min-w-0 text-truncate-chat" 
                            title={session.title}
                          >
                            {session.title.length > 22 ? `${session.title.substring(0, 22)}...` : session.title}
                          </div>
                          {session.selectedModel && (
                            <Badge 
                              variant="outline" 
                              className={cn(
                                "text-xs px-1 py-0 h-4 font-normal shrink-0",
                                session.selectedModel === 'deepseek-r1' 
                                  ? "bg-purple-100 border-purple-300 text-purple-700 dark:bg-purple-900/30 dark:border-purple-600 dark:text-purple-300"
                                  : session.selectedModel === 'llama-3.1-8b-q4'
                                    ? "bg-yellow-100 border-yellow-300 text-yellow-700 dark:bg-yellow-900/30 dark:border-yellow-600 dark:text-yellow-300"
                                    : "bg-blue-100 border-blue-300 text-blue-700 dark:bg-blue-900/30 dark:border-blue-600 dark:text-blue-300"
                              )}
                            >
                              {session.selectedModel === 'deepseek-r1' ? 'R1' : 'L'}
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                          <span>{formatTimeAgo(session.updatedAt || session.createdAt)}</span>
                          <span>•</span>
                          <span>{estimateTokens(session)}</span>
                          {session.messages?.length ? (<>
                            <span>•</span>
                            <span>{session.messages.length} msgs</span>
                          </>) : null}
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="absolute top-1 right-1 h-5 w-5 opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteSession(session.id);
                        }}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </ScrollArea>

        </div>
      </div>
    </>
  );
}
