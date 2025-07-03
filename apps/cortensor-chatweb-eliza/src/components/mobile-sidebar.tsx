"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { Badge } from "@/components/ui/badge"
import { Menu, MessageCircle, Plus, Trash2, Bot } from "lucide-react"
import type { ChatSession } from "@/lib/storage"
import { NetworkStatus } from "./network-status"
import { config } from "@/lib/config"

interface MobileSidebarProps {
  sessions: ChatSession[]
  currentSessionId: string
  onNewSession: () => void
  onLoadSession: (sessionId: string) => void
  onDeleteSession: (sessionId: string) => void
}

export function MobileSidebar({
  sessions,
  currentSessionId,
  onNewSession,
  onLoadSession,
  onDeleteSession,
}: MobileSidebarProps) {
  const [open, setOpen] = useState(false)

  const handleNewSession = () => {
    onNewSession()
    setOpen(false)
  }

  const handleLoadSession = (sessionId: string) => {
    onLoadSession(sessionId)
    setOpen(false)
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden">
          <Menu className="h-5 w-5" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-80 p-0">
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-4 border-b">
            <div className="flex items-center gap-2 mb-4">
              <Bot className="h-6 w-6" />
              <div>
                <h1 className="text-xl font-bold">{config.app.name}</h1>
                <p className="text-xs text-muted-foreground">v{config.app.version}</p>
              </div>
            </div>
            <Button onClick={handleNewSession} className="w-full" variant="outline">
              <Plus className="h-4 w-4 mr-2" />
              New Chat
            </Button>
          </div>

          {/* Sessions List */}
          <div className="flex-1 overflow-auto p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-muted-foreground">Chat History</h3>
              <Badge variant="secondary" className="text-xs">
                {sessions.length}
              </Badge>
            </div>
            <div className="space-y-2">
              {sessions.map((session) => (
                <div key={session.id} className="flex items-center group">
                  <button
                    onClick={() => handleLoadSession(session.id)}
                    className={`flex-1 text-left p-3 rounded-lg transition-colors ${
                      session.id === currentSessionId ? "bg-primary text-primary-foreground" : "hover:bg-muted"
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <MessageCircle className="h-4 w-4 flex-shrink-0" />
                      <span className="font-medium truncate">{session.title}</span>
                    </div>
                    <div className="text-xs opacity-70 flex items-center gap-2">
                      <span>{session.createdAt.toLocaleDateString()}</span>
                      {session.blockchainSessionId && (
                        <Badge variant="outline" className="text-xs px-1 py-0">
                          #{session.blockchainSessionId}
                        </Badge>
                      )}
                    </div>
                  </button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity ml-2"
                    onClick={(e) => {
                      e.stopPropagation()
                      onDeleteSession(session.id)
                    }}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="p-4 border-t">
            <NetworkStatus />
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
