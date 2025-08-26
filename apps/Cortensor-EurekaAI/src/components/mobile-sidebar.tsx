"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { Badge } from "@/components/ui/badge"
import { Menu, MessageCircle, Plus, Trash2, Bot } from "lucide-react"
import type { ChatSession } from "@/lib/storage"

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
      <SheetContent side="left" className="w-72 p-0 sm:w-80 mobile-sheet">
        <div className="flex flex-col h-full max-h-screen overflow-hidden">
          {/* Header */}
          <div className="p-3 border-b">
            <div className="flex items-center gap-2 mb-3">
              <Bot className="h-5 w-5" />
              <div>
                <h1 className="text-lg font-bold">Eureka</h1>
                <p className="text-xs text-muted-foreground">AI Assistant</p>
              </div>
            </div>
            <Button onClick={handleNewSession} className="w-full h-8 text-sm" variant="outline">
              <Plus className="h-3 w-3 mr-2" />
              New Chat
            </Button>
          </div>

          {/* Sessions List */}
          <div className="flex-1 overflow-auto p-3">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-medium text-muted-foreground">Chat History</h3>
              <Badge variant="secondary" className="text-xs h-4 px-1.5">
                {sessions.length}
              </Badge>
            </div>
            <div className="space-y-1">
              {sessions.map((session) => (
                <div key={session.id} className="group relative">
                  <button
                    onClick={() => handleLoadSession(session.id)}
                    className={`w-full text-left p-2 pr-8 rounded-md transition-colors ${
                      session.id === currentSessionId ? "bg-primary text-primary-foreground" : "hover:bg-muted"
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <MessageCircle className="h-3 w-3 flex-shrink-0" />
                      <span className="font-medium text-sm truncate flex-1 min-w-0">{session.title}</span>
                    </div>
                    <div className="text-xs opacity-70 flex items-center justify-start">
                      <Badge variant="outline" className="text-xs px-1 py-0 h-4">
                        {session.messages.length}
                      </Badge>
                    </div>
                  </button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute top-1 right-1 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
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
            <div className="flex items-center justify-center text-xs text-muted-foreground">
              <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
              Connected to Cortensor Network
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
