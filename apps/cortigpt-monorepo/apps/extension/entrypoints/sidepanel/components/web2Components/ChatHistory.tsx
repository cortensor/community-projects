'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  MessageSquare,
  Clock,
  Trash2,
  Plus,
  Search
} from 'lucide-react'
import { Input } from '@/components/ui/input'
import { formatDistanceToNow } from 'date-fns'
import { cn } from '@/lib/utils'
import { useWeb2Chat, ChatHistoryItem } from '@/stores/useWeb2ChatStore'

interface ChatHistoryProps {
  className?: string
  userAddress: string // User address for user-specific history
}

export function ChatHistory({ className, userAddress }: ChatHistoryProps) {
  const [searchQuery, setSearchQuery] = useState('')
  
  // Use Web2 Zustand store
  const {
    chatHistory,
    selectedChatId,
    setUserAddress,
    createNewChat,
    switchToChat,
    deleteChat
  } = useWeb2Chat()

  // Initialize user address in store
  useEffect(() => {
    if (userAddress) {
      setUserAddress(userAddress)
    }
  }, [userAddress, setUserAddress])

  // Wrapper functions for store actions
  const handleCreateNewChat = () => {
    createNewChat()
  }

  const handleSwitchToChat = (chatId: string) => {
    switchToChat(chatId)
  }

  const handleDeleteChat = (chatId: string) => {
    deleteChat(chatId)
  }

  // Filter chats based on search query
  const filteredChats = chatHistory.filter(chat =>
    chat.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    chat.lastMessage.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <Card className={cn(
      "h-full backdrop-blur-xl bg-card/50 border-border/50 shadow-glass",
      className
    )}>
      <CardHeader className="pb-3">
        <div className="flex justify-between items-center">
          <CardTitle className="text-lg font-futura text-foreground">
            Chat History
          </CardTitle>
          <Button
              onClick={handleCreateNewChat}
              size="sm"
              className="p-0 w-8 h-8"
            >
            <Plus className="w-4 h-4" />
          </Button>
        </div>

        {/* Search Input */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 w-4 h-4 transform -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search chats..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 h-9"
          />
        </div>
      </CardHeader>

      <CardContent className="p-0">
        <ScrollArea className="h-[calc(100vh-200px)]">
          <div className="p-4 space-y-2">
            {filteredChats.length === 0 ? (
              <div className="py-8 text-center">
                <MessageSquare className="mx-auto mb-4 w-12 h-12 text-muted-foreground" />
                <p className="mb-4 text-sm text-muted-foreground">
                  {searchQuery ? 'No chats found' : 'No chat history yet'}
                </p>
                {!searchQuery && (
                  <Button onClick={handleCreateNewChat} size="sm">
                    <Plus className="mr-2 w-4 h-4" />
                    Start New Chat
                  </Button>
                )}
              </div>
            ) : (
              filteredChats.map((chat) => (
                <div
                  key={chat.id}
                  className={cn(
                    "group relative p-3 rounded-lg border cursor-pointer transition-all duration-200 hover:bg-muted/50",
                    selectedChatId === chat.id
                      ? "bg-primary/10 border-primary/50"
                      : "bg-muted/20 border-border/50"
                  )}
                  onClick={() => handleSwitchToChat(chat.id)}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1 min-w-0">
                      <div className="flex gap-2 items-center mb-1">
                        <h4 className="text-sm font-medium truncate text-foreground">
                          {chat.title}
                        </h4>
                        <Badge variant="secondary" className="text-xs px-1.5 py-0">
                          {chat.messageCount}
                        </Badge>
                      </div>
                      <p className="mb-2 text-xs truncate text-muted-foreground">
                        {chat.lastMessage}
                      </p>
                      <div className="flex gap-1 items-center text-xs text-muted-foreground">
                        <Clock className="w-3 h-3" />
                        <span>{formatDistanceToNow(chat.timestamp, { addSuffix: true })}</span>
                      </div>
                    </div>

                    <Button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeleteChat(chat.id)
                      }}
                      size="sm"
                      variant="ghost"
                      className="p-0 w-6 h-6 opacity-0 transition-opacity group-hover:opacity-100 text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}