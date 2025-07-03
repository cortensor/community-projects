"use client"

import { Card, CardContent } from "./ui/card"
import { ScrollArea } from "./ui/scroll-area"
import { Badge } from "./ui/badge"
import { Bot, User } from "lucide-react"
import { SessionHeader } from "./session-header"
import type { ChatSession, ChatMessage } from "../lib/storage"
import { appConfig } from "../lib/app-config"
import { cn } from "../lib/utils"

interface MainContentProps {
  currentSession: ChatSession | undefined
  messages: ChatMessage[]
  isLoading: boolean
  isPanelOpen: boolean
  isMobile: boolean
}

export function MainContent({ currentSession, messages, isLoading, isPanelOpen, isMobile }: MainContentProps) {
  return (
    <div
      className={cn(
        "flex-1 flex flex-col min-h-0 transition-all duration-300 ease-in-out",
        isPanelOpen && !isMobile && "ml-80",
      )}
    >
      <header className="border-b p-4 bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/60 border-border/50">
        <div
          className={cn(
            "flex items-center gap-2 transition-all duration-300 ease-in-out",
            isPanelOpen && !isMobile && "ml-16",
          )}
        >
          <Bot className="h-5 w-5" />
          <h2 className="text-lg font-semibold">{appConfig.app.assistant}</h2>
        </div>
      </header>

      {currentSession && (
        <div
          className={cn(
            "border-b border-border/50 bg-background/40 backdrop-blur-sm transition-all duration-300 ease-in-out",
            isPanelOpen && !isMobile && "ml-16",
          )}
        >
          <SessionHeader session={currentSession} isActive={true} />
        </div>
      )}

      <div className="flex-1 flex flex-col min-h-0">
        <ScrollArea className="flex-1">
          <div className={cn("p-4 transition-all duration-300 ease-in-out", isPanelOpen && !isMobile && "ml-16")}>
            <div className="max-w-4xl mx-auto space-y-4">
              {messages.length === 0 ? (
                <Card className="p-6 sm:p-8 text-center bg-background/60 backdrop-blur-sm border-border/50 shadow-lg">
                  <Bot className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                  <h3 className="text-lg font-medium mb-2">Welcome to {appConfig.app.name}</h3>
                  <p className="text-muted-foreground mb-4">
                    Start a conversation with {appConfig.app.assistant}.
                  </p>
                  {currentSession?.cortensorSessionId && (
                    <Badge variant="outline" className="text-sm bg-background/50">
                      Session #{currentSession.cortensorSessionId} Active
                    </Badge>
                  )}
                </Card>
              ) : (
                messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    {message.role === "assistant" && (
                      <div className="flex-shrink-0">
                        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shadow-sm">
                          <Bot className="h-4 w-4 text-primary-foreground" />
                        </div>
                      </div>
                    )}
                    <Card
                      className={`max-w-[85%] sm:max-w-[75%] shadow-sm backdrop-blur-sm border-border/50 ${
                        message.role === "user" ? "bg-primary/90 text-primary-foreground" : "bg-background/60"
                      }`}
                    >
                      <CardContent className="p-3 sm:p-4">
                        <div className="whitespace-pre-wrap text-sm sm:text-base leading-relaxed">
                          {message.content}
                        </div>
                        <div className="text-xs opacity-70 mt-2">
                          {new Date(message.timestamp).toLocaleTimeString()}
                        </div>
                      </CardContent>
                    </Card>
                    {message.role === "user" && (
                      <div className="flex-shrink-0">
                        <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center shadow-sm">
                          <User className="h-4 w-4" />
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
              {isLoading && (
                <div className="flex gap-3 justify-start">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shadow-sm">
                      <Bot className="h-4 w-4 text-primary-foreground animate-pulse" />
                    </div>
                  </div>
                  <Card className="bg-background/60 backdrop-blur-sm border-border/50 shadow-sm">
                    <CardContent className="p-3 sm:p-4">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-current rounded-full animate-bounce"></div>
                        <div
                          className="w-2 h-2 bg-current rounded-full animate-bounce"
                          style={{ animationDelay: "0.1s" }}
                        ></div>
                        <div
                          className="w-2 h-2 bg-current rounded-full animate-bounce"
                          style={{ animationDelay: "0.2s" }}
                        ></div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}
            </div>
          </div>
        </ScrollArea>
      </div>
    </div>
  )
}
