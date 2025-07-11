// src/components/main-content.tsx
"use client"

import { Card, CardContent } from "./ui/card"
import { ScrollArea } from "./ui/scroll-area"
import { Bot, User, BrainCircuit } from "lucide-react"
import type { ChatSession, ChatMessage } from "../lib/storage"
import { appConfig } from "../lib/app-config"
import { cn } from "../lib/utils"
import { Skeleton } from "./ui/skeleton"
import { Switch } from "./ui/switch"
import { Label } from "./ui/label"

// Indicator for when a response is being generated
const ThinkingIndicator = () => (
  <div className="flex gap-3 justify-start">
    <div className="flex-shrink-0">
      <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shadow-sm">
        <Bot className="h-4 w-4 text-primary-foreground" />
      </div>
    </div>
    <Card className="max-w-[85%] sm:max-w-[75%] shadow-sm backdrop-blur-sm border-border/50 bg-background/60">
      <CardContent className="p-3 sm:p-4">
        <div className="flex items-center gap-2 text-sm font-medium">
          <div className="w-2 h-2 bg-current rounded-full animate-bounce"></div>
          <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: "0.1s" }}></div>
          <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
          <span>Assistant is thinking...</span>
        </div>
        <Skeleton className="h-4 w-48 mt-3" />
        <Skeleton className="h-4 w-32 mt-2" />
      </CardContent>
    </Card>
  </div>
);

// Indicator for when the initial device session is being created
const InitializingIndicator = () => (
  <Card className="p-6 sm:p-8 text-center bg-background/60 backdrop-blur-sm border-border/50 shadow-lg">
    <div className="flex justify-center items-center gap-4">
      <div className="w-4 h-4 bg-primary rounded-full animate-ping"></div>
      <h3 className="text-lg font-medium">Initializing Secure Session...</h3>
    </div>
    <p className="text-muted-foreground mt-2 text-sm">
      Please wait, this may take up to a minute while confirming on the blockchain.
    </p>
  </Card>
);

interface MainContentProps {
  currentSession: ChatSession | undefined
  messages: ChatMessage[]
  isLoading: boolean
  isPanelOpen: boolean
  isMobile: boolean
  isMemoryMode: boolean
  onMemoryModeChange: (checked: boolean) => void
}

export function MainContent({
  currentSession,
  messages,
  isLoading,
  isPanelOpen,
  isMobile,
  isMemoryMode,
  onMemoryModeChange
}: MainContentProps) {
  return (
    <div className={cn("flex-1 flex flex-col min-h-0 transition-all duration-300 ease-in-out", isPanelOpen && !isMobile && "ml-80")}>
      <header className="flex items-center justify-between border-b p-4 bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/60 border-border/50">
        <div className={cn("flex items-center gap-2 transition-all duration-300 ease-in-out", isPanelOpen && !isMobile && "ml-16")}>
          <Bot className="h-5 w-5" />
          <h2 className="text-lg font-semibold">{appConfig.app.assistant}</h2>
        </div>
        <div className="flex items-center space-x-2">
          <BrainCircuit className="h-4 w-4 text-muted-foreground" />
          <Label htmlFor="memory-mode" className="text-sm font-medium text-muted-foreground">
            Memory Mode
          </Label>
          <Switch
            id="memory-mode"
            checked={isMemoryMode}
            onCheckedChange={onMemoryModeChange}
          />
        </div>
      </header>

      <div className="flex-1 flex flex-col min-h-0">
        <ScrollArea className="flex-1">
          <div className={cn("p-4 transition-all duration-300 ease-in-out", isPanelOpen && !isMobile && "ml-16")}>
            <div className="max-w-4xl mx-auto space-y-4">
              {/* Conditional Rendering Logic */}
              {isLoading && messages.length === 0 ? (
                <InitializingIndicator />
              ) : messages.length === 0 && !isLoading ? (
                <Card className="p-6 sm:p-8 text-center bg-background/60 backdrop-blur-sm border-border/50 shadow-lg">
                  <Bot className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                  <h3 className="text-lg font-medium mb-2">Welcome to {appConfig.app.name}</h3>
                  <p className="text-muted-foreground mb-4">How can I help you today?</p>
                </Card>
              ) : (
                messages.map((message) => (
                  <div key={message.id} className={`flex gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                    {message.role === "assistant" && (
                      <div className="flex-shrink-0">
                        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shadow-sm">
                          <Bot className="h-4 w-4 text-primary-foreground" />
                        </div>
                      </div>
                    )}
                    <Card className={`max-w-[85%] sm:max-w-[75%] shadow-sm backdrop-blur-sm border-border/50 ${message.role === "user" ? "bg-primary/90 text-primary-foreground" : "bg-background/60"}`}>
                      <CardContent className="p-3 sm:p-4">
                        <div className="whitespace-pre-wrap text-sm sm:text-base leading-relaxed">{message.content}</div>
                        <div className="text-xs opacity-70 mt-2">{new Date(message.timestamp).toLocaleTimeString()}</div>
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
              {isLoading && messages.length > 0 && <ThinkingIndicator />}
            </div>
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}
