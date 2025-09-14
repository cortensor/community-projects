"use client";

import React, { useState, useEffect } from 'react';
import { useNewChat } from '@/hooks/useNewChat';
import { useChatCompletion } from '@/hooks/useChatCompletion';
import { usePersonas } from '@/hooks/usePersonas';
import { useModels } from '@/hooks/useModels';
import { useDomains } from '@/hooks/useDomains';
import Sidebar from '@/components/sidebar/Sidebar';
import ChatHeader from '@/components/chat/ChatHeader';
import MessageList from '@/components/chat/MessageList';
import StatusBanners from '@/components/chat/StatusBanners';
import ChatInputForm from '@/components/chat/ChatInputForm';
import { ChatSession } from '@/types';
import ChatPageSkeleton from '@/components/chat/ChatPageSkeleton';
import { SseProvider } from '@/context/SseContext';

export default function ChatPage() {
  const {
    // State
    currentSession,
    allSessions,
    isSidebarOpen,
    isResearchMode,
    user,
    sessionConfig,
    isMemoryEnabled,
    supportsResearch,
    
    // Actions
    handleNewChat,
    handleSelectChat,
    handleDeleteChat,
    handleRenameChat,
    handleToggleSidebar,
    handleToggleResearch,
    
    // Session config actions
    setSessionModel,
    setSessionDomain,
    setSessionPersona,
    toggleSessionMemory,
  } = useNewChat();
  
  // For backward compatibility with existing components
  const { personas } = usePersonas();
  const { models } = useModels();
  const { domains } = useDomains();

  const {
    inputValue,
    error,
    inputRef,
    messagesEndRef,
    handleInputChange,
    handleSubmit: handleCompletionSubmit,
    handleSelectResponse,
  } = useChatCompletion(
    allSessions,
    currentSession?.id || null,
    undefined, // No longer needed
    personas.find(p => p.id === sessionConfig?.personaId),
    models.find(m => m.id === sessionConfig?.modelId),
    domains.find(d => d.id === sessionConfig?.domainId),
    isMemoryEnabled,
  );

  const isLoading = currentSession?.isLoading || false;
  const loadingMessage = currentSession?.loadingMessage || null;

  const currentMessages = currentSession?.messages || [];
  const displayError = error && error.chatId === currentSession?.id ? error.message : null;

  const handleFormSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    let chatId = currentSession?.id;
    if (!chatId) {
      const newChatId = handleNewChat();
      if (!newChatId) return;
      chatId = newChatId;
    }
    await handleCompletionSubmit(e, { chatId });
  };

  const toggleSidebar = handleToggleSidebar;

  const handleNewChatAndToggle = () => {
    handleNewChat();
    if (window.innerWidth < 768 && isSidebarOpen) handleToggleSidebar();
  }

  const handleSelectChatAndToggle = (chatId: string) => {
    handleSelectChat(chatId);
    if (window.innerWidth < 768 && isSidebarOpen) handleToggleSidebar();
  }

  if (!user.userId) {
    return <ChatPageSkeleton />;
  }

  return (
    <SseProvider>
      {/* Enhanced backdrop for mobile sidebar */}
      {isSidebarOpen && (
        <div
          onClick={toggleSidebar}
          className="fixed inset-0 z-10 bg-black/80 backdrop-blur-sm md:hidden"
        />
      )}
      
      {/* Main gradient background */}
      <div className="fixed inset-0 bg-gradient-to-br from-slate-900 via-black to-slate-800">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-blue-900/20 via-transparent to-purple-900/20"></div>
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,_var(--tw-gradient-stops))] from-indigo-900/20 via-transparent to-cyan-900/20"></div>
      </div>
      
      <div className="relative z-0 flex h-screen text-white font-sans antialiased">
        <Sidebar
          userId={user.userId}
          isSidebarOpen={isSidebarOpen}
          toggleSidebar={toggleSidebar}
          chatSessions={allSessions}
          currentChatId={currentSession?.id || null}
          onNewChat={handleNewChatAndToggle}
          onSelectChat={handleSelectChatAndToggle}
          onDeleteChat={handleDeleteChat}
          onRenameChat={handleRenameChat}
        />
        <div className="flex-1 flex flex-col">
          <ChatHeader
            isSidebarOpen={isSidebarOpen}
            toggleSidebar={toggleSidebar}
            currentChatId={currentSession?.id || null}
            chatSessions={allSessions}
            personas={personas}
            selectedPersona={personas.find(p => p.id === sessionConfig?.personaId)}
            onSelectPersona={(id) => setSessionPersona && setSessionPersona(id)}
            models={models}
            selectedModel={models.find(m => m.id === sessionConfig?.modelId)}
            onSelectModel={(id) => setSessionModel && setSessionModel(id)}
            isMemoryEnabled={isMemoryEnabled}
            onToggleMemory={toggleSessionMemory || (() => {})}
            domains={domains}
            selectedDomain={domains.find(d => d.id === sessionConfig?.domainId)}
            onSelectDomain={(id) => setSessionDomain && setSessionDomain(id)}
          />

          <div className="flex-1 relative overflow-y-scroll custom-scrollbar">
            <MessageList messages={currentMessages} messagesEndRef={messagesEndRef} handleSelectResponse={handleSelectResponse} isLoading={isLoading} loadingMessage={loadingMessage} />

            <div className="absolute bottom-0 left-0 w-full h-56 bg-gradient-to-t from-black via-black/80 to-transparent pointer-events-none" />

            <div className="absolute bottom-0 left-0 w-full">
              <StatusBanners isLoading={false} error={displayError} />
              <ChatInputForm 
                inputValue={inputValue} 
                onInputChange={handleInputChange} 
                onSubmit={handleFormSubmit} 
                inputRef={inputRef} 
                isLoading={isLoading}
                isResearchMode={isResearchMode}
                onResearchToggle={handleToggleResearch}
                showResearchToggle={supportsResearch}
              />
            </div>
          </div>
        </div>
      </div>
    </SseProvider>
  );
}