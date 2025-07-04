"use client"

import React, { useState, useEffect, useRef, useCallback } from "react"
import { ChatStorage, type ChatSession, type ChatMessage } from "@/lib/storage"
import { SlidingPanel } from "@/components/sliding-panel"
import { MainContent } from "@/components/main-content"
import { ChatInput } from "@/components/chat-input"
import { BackgroundPattern } from "@/components/background-pattern"
import { useToast } from "@/components/ui/use-toast"

export default function CortensorAIChat() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [isPanelOpen, setIsPanelOpen] = useState(true);
  const { toast } = useToast();
  
  const initialLoadRef = useRef(true);

  // Creates a new session on the Cortensor server and then in the frontend state
  const handleNewSession = useCallback(async () => {
    if (isCreatingSession || isLoading) return;
    
    setIsCreatingSession(true);
    try {
      // 1. Call our backend to create a session on the Cortensor router
      const response = await fetch('/api/session/create', { method: 'POST' });
      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || "Failed to create a new session on the server.");
      }
      
      const { cortensorSessionId } = data;
      
      // 2. Create the session in the frontend state with the real ID from Cortensor
      const now = new Date();
      const newSession: ChatSession = {
        id: now.getTime().toString(), // Local ID for UI keys
        cortensorSessionId: cortensorSessionId, // Store the real identifier
        title: "New Chat",
        messages: [],
        createdAt: now,
        updatedAt: now,
      };
      
      const newSessions = [newSession, ...sessions];
      setSessions(newSessions);
      setCurrentSessionId(newSession.id);
      setMessages([]);
      ChatStorage.saveSessions(newSessions);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "An unknown error occurred.";
      toast({
        variant: "destructive",
        title: "Error Creating Session",
        description: errorMessage,
      });
    } finally {
      setIsCreatingSession(false);
    }
  }, [isCreatingSession, isLoading, sessions, toast]);

  // Load sessions from Local Storage on initial render
  useEffect(() => {
    if (initialLoadRef.current) {
        initialLoadRef.current = false;
        const savedSessions = ChatStorage.loadSessions();
        if (savedSessions.length > 0) {
          setSessions(savedSessions);
          const latestSession = savedSessions[0];
          setCurrentSessionId(latestSession.id);
          setMessages(latestSession.messages);
        }
    }
  }, []);

  // Persist session changes to Local Storage
  useEffect(() => {
    if (!initialLoadRef.current && currentSessionId) {
        const updatedSessions = sessions.map(session =>
            session.id === currentSessionId
              ? { ...session, messages: messages, updatedAt: new Date(), title: messages[0]?.content.substring(0, 30) || session.title }
              : session
          );
        setSessions(updatedSessions);
        ChatStorage.saveSessions(updatedSessions);
    }
  }, [messages, currentSessionId]);
  
  const loadSession = (sessionId: string) => {
    const session = sessions.find((s) => s.id === sessionId);
    if (session) {
      setCurrentSessionId(sessionId);
      setMessages(session.messages);
    }
  };

  const deleteSession = (sessionId: string) => {
    const updatedSessions = sessions.filter((s) => s.id !== sessionId);
    setSessions(updatedSessions);
    ChatStorage.saveSessions(updatedSessions);
    if (sessionId === currentSessionId) {
      if (updatedSessions.length > 0) {
        loadSession(updatedSessions[0].id);
      } else {
        setCurrentSessionId("");
        setMessages([]);
      }
    }
  };

  // Handles submitting the chat message
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim() || isLoading || !currentSessionId) return;
    
    const currentSession = sessions.find(s => s.id === currentSessionId);
    if (!currentSession || !currentSession.cortensorSessionId) {
        toast({
            variant: "destructive",
            title: "Invalid Session Error",
            description: "This session does not have a valid ID from Cortensor. Please create a new session.",
        });
        return;
    }

    setIsLoading(true);
    const userMessage: ChatMessage = { id: Date.now().toString(), role: 'user', content: input, timestamp: new Date() };
    const newMessages = [...messages, userMessage];
    
    setMessages(newMessages);
    setInput('');

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            messages: newMessages,
            cortensorSessionId: currentSession.cortensorSessionId // Send the real session identifier
        })
      });

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || "Failed to get a response from the AI.");
      }
      
      const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.message,
          timestamp: new Date()
      };
      setMessages(current => [...current, assistantMessage]);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to connect to the server.";
      const errorAssistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `❌ Error: ${errorMessage}`,
          timestamp: new Date()
      };
      setMessages(current => [...current, errorAssistantMessage]);
    } finally {
        setIsLoading(false);
    }
  };

  return (
    <div className="h-screen overflow-hidden relative">
      <BackgroundPattern />
      <SlidingPanel
        sessions={sessions}
        currentSessionId={currentSessionId}
        onNewSession={handleNewSession}
        onLoadSession={loadSession}
        onDeleteSession={deleteSession}
        isOpen={isPanelOpen}
        onToggle={() => setIsPanelOpen(!isPanelOpen)}
        isMobile={false}
        isCreatingSession={isCreatingSession}
      />
      <div className="flex flex-col h-full relative z-10">
        <MainContent
          messages={messages}
          isLoading={isLoading || isCreatingSession}
          isPanelOpen={isPanelOpen}
          hasActiveSession={!!currentSessionId}
        />
        <ChatInput
          input={input}
          isLoading={isLoading || isCreatingSession}
          onInputChange={(e) => setInput(e.target.value)}
          onSubmit={handleSubmit}
          disabled={!currentSessionId}
        />
      </div>
    </div>
  );
}
