// src/app/page.tsx
"use client"

import React, { useState, useEffect, useCallback } from "react"
import { ChatStorage, type ChatSession, type ChatMessage } from "@/lib/storage"
import { SlidingPanel } from "@/components/sliding-panel"
import { MainContent } from "@/components/main-content"
import { ChatInput } from "@/components/chat-input"
import { BackgroundPattern } from "@/components/background-pattern"
import { useToast } from "@/components/ui/use-toast"
import { appConfig } from "@/lib/app-config"

export default function CortensorAIChat() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isPanelOpen, setIsPanelOpen] = useState(true);
  const { toast } = useToast();
  const [isMemoryMode, setIsMemoryMode] = useState(true);

  // Fungsi untuk membuat riwayat obrolan lokal baru
  const handleNewChat = useCallback(() => {
    const newChat: ChatSession = {
      id: Date.now().toString(),
      cortensorSessionId: appConfig.chat.staticSessionId,
      title: "New Chat",
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    setSessions(prev => [...prev, newChat]);
    setCurrentChatId(newChat.id);
    setMessages([]);
    toast({ title: "New chat started." });
  }, []);

  // Inisialisasi dari local storage. Tidak ada lagi panggilan ke server.
  useEffect(() => {
    const localHistories = ChatStorage.loadSessions();
    if (localHistories.length > 0) {
      setSessions(localHistories);
      const lastActiveId = localStorage.getItem('lastActiveSessionId');
      const sessionToLoad = localHistories.find(s => s.id === lastActiveId) || localHistories[localHistories.length - 1];
      setCurrentChatId(sessionToLoad.id);
      setMessages(sessionToLoad.messages);
    } else {
      // Jika tidak ada riwayat sama sekali, buat yang pertama
      handleNewChat();
    }
  }, [handleNewChat]);

  // Efek untuk menyimpan perubahan ke local storage
  useEffect(() => {
    if (currentChatId) {
      localStorage.setItem('lastActiveSessionId', currentChatId);
      const updatedSessions = sessions.map(session =>
        session.id === currentChatId
          ? { ...session, messages, title: session.title, updatedAt: new Date() }
          : session
      );
      ChatStorage.saveSessions(updatedSessions);
    }
  }, [messages, currentChatId, sessions]);

  const loadLocalChat = (chatId: string) => {
    const session = sessions.find(s => s.id === chatId);
    if (session) {
      setCurrentChatId(session.id);
      setMessages(session.messages);
    }
  };
  
  const handleDeleteSession = (chatId: string) => {
    const updatedSessions = sessions.filter(s => s.id !== chatId);
    setSessions(updatedSessions);
    if (currentChatId === chatId) {
      if (updatedSessions.length > 0) {
        loadLocalChat(updatedSessions[updatedSessions.length - 1].id);
      } else {
        handleNewChat();
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim() || isLoading || !currentChatId) return;

    if (messages.length === 0) {
      const newTitle = input.length > 30 ? input.substring(0, 27) + '...' : input;
      setSessions(prevSessions => prevSessions.map(session =>
        session.id === currentChatId ? { ...session, title: newTitle } : session
      ));
    }

    const userMessage: ChatMessage = { id: Date.now().toString(), role: 'user', content: input, timestamp: new Date() };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    
    const payloadMessages = isMemoryMode ? [...messages, userMessage] : [userMessage];
    
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            messages: payloadMessages,
            cortensorSessionId: appConfig.chat.staticSessionId
        })
      });

      const result = await response.json();

      if (!response.ok || !result.success) {
        throw new Error(result.error || "An unknown error occurred.");
      }

      const assistantMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: result.message,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, assistantMessage]);

    } catch (error: any) {
      const errorMessage = error.message || "An unexpected error occurred. Please try again.";
      const errorAssistantMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `❌ Error: ${errorMessage}`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorAssistantMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-screen overflow-hidden relative">
      <BackgroundPattern />
      <SlidingPanel
        sessions={sessions}
        currentSessionId={currentChatId}
        onNewSession={handleNewChat}
        onLoadSession={loadLocalChat}
        onDeleteSession={handleDeleteSession}
        isOpen={isPanelOpen}
        onToggle={() => setIsPanelOpen(!isPanelOpen)}
        isMobile={false}
      />
      <div className="flex flex-col h-full relative z-10">
        <MainContent
          currentSession={sessions.find(s => s.id === currentChatId)}
          messages={messages}
          isLoading={isLoading}
          isPanelOpen={isPanelOpen}
          isMobile={false}
          isMemoryMode={isMemoryMode}
          onMemoryModeChange={setIsMemoryMode}
        />
        <ChatInput
          input={input}
          isLoading={isLoading}
          onInputChange={(e) => setInput(e.target.value)}
          onSubmit={handleSubmit}
          disabled={isLoading || !currentChatId}
          isPanelOpen={isPanelOpen}
          isMobile={false}
        />
      </div>
    </div>
  );
}
