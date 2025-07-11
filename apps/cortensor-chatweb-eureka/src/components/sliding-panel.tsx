// src/components/sliding-panel.tsx
"use client"

import { Button } from "./ui/button"
import { Badge } from "./ui/badge"
import { ScrollArea } from "./ui/scroll-area"
import { PanelLeftOpen, PanelLeftClose, MessageCircle, Plus, Trash2, Bot, X } from "lucide-react"
import { appConfig } from "@/lib/app-config"
import type { ChatSession } from "@/lib/storage"
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
}: SlidingPanelProps) {
  const sessionList = Array.isArray(sessions) ? sessions.slice().reverse() : [];

  return (
    <>
      <Button
        variant="ghost"
        size="icon"
        onClick={onToggle}
        className={cn(
          "fixed top-4 left-4 z-50 bg-background/80 backdrop-blur-md border shadow-lg hover:bg-background/90 transition-all duration-300 ease-in-out border-border/50",
          isOpen && !isMobile && "left-[336px]",
        )}
      >
        {isOpen ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
      </Button>

      {isMobile && isOpen && <div className="fixed inset-0 bg-black/50 z-40 md:hidden" onClick={onToggle} />}

      <div
        className={cn(
          "fixed left-0 top-0 h-full w-80 bg-background/80 backdrop-blur-md border-r shadow-xl z-40 transition-transform duration-300 ease-in-out border-border/50",
          !isOpen && "-translate-x-full",
          isMobile && "z-50",
        )}
      >
        <div className="flex flex-col h-full">
          <div className="p-4 border-b border-border/50">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Bot className="h-6 w-6" />
                <div>
                  <h1 className="text-xl font-bold">{appConfig.app.name}</h1>
                  <p className="text-xs text-muted-foreground">v{appConfig.app.version}</p>
                </div>
              </div>
              {isMobile && (
                <Button variant="ghost" size="icon" onClick={onToggle} className="h-8 w-8">
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
            <Button onClick={onNewSession} className="w-full shadow-sm" variant="outline">
              <Plus className="h-4 w-4 mr-2" />
              New Chat
            </Button>
          </div>

          <ScrollArea className="flex-1">
            <div className="p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-muted-foreground">Chat History</h3>
                <Badge variant="secondary" className="text-xs bg-background/50">
                  {sessionList.length}
                </Badge>
              </div>

              <div className="space-y-2">
                {sessionList.map((session) => (
                  <div
                    key={session.id}
                    className={cn(
                      "group relative rounded-lg border p-3 cursor-pointer transition-all hover:bg-muted/50 border-border/50 backdrop-blur-sm",
                      session.id === currentSessionId
                        ? "bg-primary/10 border-primary/20 shadow-sm"
                        : "bg-background/30",
                    )}
                    onClick={() => {
                      onLoadSession(session.id);
                      if (isMobile) onToggle();
                    }}
                  >
                    <div className="flex items-start gap-3">
                      <MessageCircle className="h-4 w-4 mt-0.5 flex-shrink-0 text-muted-foreground" />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm truncate">{session.title}</div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {new Date(session.createdAt).toLocaleDateString()}
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
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
