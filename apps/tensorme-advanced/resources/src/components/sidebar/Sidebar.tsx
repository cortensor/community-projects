"use client";
import React from 'react';
import { ChatSession } from '@/types';
import SidebarHeader from './SidebarHeader';
import NewChatButton from './NewChatButton';
import ChatListItem from './ChatListItem';
import ResetStorageButton from './ResetStorageButton';

interface SidebarProps {
  userId: string | null;
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  chatSessions: ChatSession[];
  currentChatId: string | null;
  onNewChat: () => void;
  onSelectChat: (chatId: string) => void;
  onDeleteChat: (chatId: string, event: React.MouseEvent<HTMLButtonElement>) => void;
  onRenameChat: (chatId: string, newName: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  userId,
  isSidebarOpen,
  toggleSidebar,
  chatSessions,
  currentChatId,
  onNewChat,
  onSelectChat,
  onDeleteChat,
  onRenameChat,
}) => {
  const handleNewChatAndCloseSidebar = () => {
    onNewChat();
    if (window.innerWidth < 768 && isSidebarOpen) {
      toggleSidebar();
    }
  }

  const handleSelectChatAndCloseSidebar = (chatId: string) => {
    onSelectChat(chatId);
    if (window.innerWidth < 768 && isSidebarOpen) {
      toggleSidebar();
    }
  }

  return (
    <aside className={`fixed z-20 inset-y-0 left-0 backdrop-blur-xl bg-black/20 border-r border-white/10 flex flex-col w-72 max-w-full ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'} md:relative md:translate-x-0 md:w-72`}>
      <SidebarHeader isSidebarOpen={isSidebarOpen} toggleSidebar={toggleSidebar} />
      <NewChatButton isSidebarOpen={isSidebarOpen} onNewChat={handleNewChatAndCloseSidebar} />
      <nav className="flex-grow p-3 space-y-2 overflow-y-auto custom-scrollbar">
        {chatSessions.map((session) => (
          <ChatListItem
            key={session.id}
            session={session}
            userId={userId}
            currentChatId={currentChatId}
            isSidebarOpen={isSidebarOpen}
            onSelectChat={handleSelectChatAndCloseSidebar}
            onDeleteChat={onDeleteChat}
            onRenameChat={onRenameChat}
          />
        ))}
      </nav>
      <div className={`p-4 border-t border-white/10 ${!isSidebarOpen && 'hidden'}`}>
        <div className="mb-3">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-2 h-2 bg-gradient-to-r from-blue-400 to-purple-500 rounded-full"></div>
            <p className="text-xs font-medium text-white/60">Cortensor Chatbot</p>
          </div>
          <p className="text-[10px] text-white/40">Enhanced with AI Research</p>
        </div>
        <ResetStorageButton />
      </div>
    </aside>
  );
};

export default Sidebar;