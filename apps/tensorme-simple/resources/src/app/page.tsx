"use client";

import React, { useState, useEffect } from 'react';
import { useUser } from '@/hooks/useUser';
import { useChatSessions } from '@/hooks/useChatSessions';
import { useChatCompletion } from '@/hooks/useChatCompletion';
import { usePersonas } from '@/hooks/usePersonas';
import Sidebar from '@/components/sidebar/Sidebar';
import ChatHeader from '@/components/chat/ChatHeader';
import MessageList from '@/components/chat/MessageList';
import StatusBanners from '@/components/chat/StatusBanners';
import ChatInputForm from '@/components/chat/ChatInputForm';
import { ChatSession } from '@/types';
import ChatPageSkeleton from '@/components/chat/ChatPageSkeleton';
import { useMemory } from '@/hooks/useMemory';
import { SseProvider } from '@/context/SseContext';

export default function ChatPage() {
  const { userId } = useUser();
  const { personas, selectedPersona, handleSelectPersona } = usePersonas();
  const { isMemoryEnabled, toggleMemory } = useMemory();
  const {
    currentChatId,
    chatSessions,
    handleNewChat,
    handleSelectChat,
    handleDeleteChat,
    handleRenameChat,
    setChatSessions,
  } = useChatSessions(userId);

  const {
    inputValue,
    error,
    inputRef,
    messagesEndRef,
    handleInputChange,
    handleSubmit: handleCompletionSubmit,
    handleSelectResponse,
  } = useChatCompletion(
    chatSessions,
    currentChatId,
    setChatSessions,
    selectedPersona,
    isMemoryEnabled,
  );

  const currentSession = chatSessions.find((session: ChatSession) => session.id === currentChatId);
  const isLoading = currentSession?.isLoading || false;
  const loadingMessage = currentSession?.loadingMessage || null;

  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const currentMessages = currentSession?.messages || [];
  const displayError = error && error.chatId === currentChatId ? error.message : null;

  const handleFormSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    let chatId = currentChatId;
    if (!chatId) {
      const newChatId = handleNewChat();
      if (!newChatId) return;
      chatId = newChatId;
    }
    await handleCompletionSubmit(e, { chatId });
  };

  useEffect(() => {
    const handleResize = () => {
      setIsSidebarOpen(window.innerWidth >= 768);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);

  const handleNewChatAndToggle = () => {
    handleNewChat();
    if (window.innerWidth < 768 && isSidebarOpen) setIsSidebarOpen(false);
  }

  const handleSelectChatAndToggle = (chatId: string) => {
    handleSelectChat(chatId);
    if (window.innerWidth < 768 && isSidebarOpen) setIsSidebarOpen(false);
  }

  if (!userId) {
    return <ChatPageSkeleton />;
  }

  return (
    <SseProvider setChatSessions={setChatSessions}>
      <div className="flex h-screen bg-neutral-base text-neutral-text-primary font-sans antialiased">
        <Sidebar userId={userId} isSidebarOpen={isSidebarOpen} toggleSidebar={toggleSidebar} chatSessions={chatSessions} currentChatId={currentChatId} onNewChat={handleNewChatAndToggle} onSelectChat={handleSelectChatAndToggle} onDeleteChat={handleDeleteChat} onRenameChat={handleRenameChat} />
        <div className="flex-1 flex flex-col bg-neutral-base">
          <ChatHeader
            isSidebarOpen={isSidebarOpen}
            toggleSidebar={toggleSidebar}
            currentChatId={currentChatId}
            chatSessions={chatSessions}
            personas={personas}
            selectedPersona={selectedPersona}
            onSelectPersona={handleSelectPersona}
            isMemoryEnabled={isMemoryEnabled}
            onToggleMemory={toggleMemory}
          />

          <div className="flex-1 relative overflow-y-hidden">
            <MessageList messages={currentMessages} messagesEndRef={messagesEndRef} handleSelectResponse={handleSelectResponse} isLoading={isLoading} loadingMessage={loadingMessage} />

            <div className="absolute bottom-0 left-0 w-full h-40 bg-gradient-to-t from-neutral-base via-neutral-base/80 to-transparent pointer-events-none" />

            <div className="absolute bottom-0 left-0 w-full">
              <StatusBanners isLoading={false} error={displayError} />
              <ChatInputForm inputValue={inputValue} onInputChange={handleInputChange} onSubmit={handleFormSubmit} inputRef={inputRef} isLoading={isLoading} />
            </div>
          </div>
        </div>
      </div>
    </SseProvider>
  );
}