"use client";
import React from 'react';
import { ChatSession } from '@/types';
import SidebarHeader from './SidebarHeader';
import NewChatButton from './NewChatButton';
import ChatListItem from './ChatListItem';
import ResetStorageButton from './ResetStorageButton'; // Import the new component

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
    <aside className={`fixed z-20 inset-y-0 left-0 bg-neutral-900 flex flex-col transition-transform duration-300 ease-in-out border-r border-neutral-800 w-72 max-w-full ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'} md:relative md:translate-x-0 md:w-72`}>
      <SidebarHeader isSidebarOpen={isSidebarOpen} toggleSidebar={toggleSidebar} />
      <NewChatButton isSidebarOpen={isSidebarOpen} onNewChat={handleNewChatAndCloseSidebar} />
      <nav className="flex-grow p-2 space-y-1 overflow-y-auto custom-scrollbar">
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
      <div className={`p-4 border-t border-neutral-800 ${!isSidebarOpen && 'hidden'}`}>
        <p className="text-xs text-gray-500">Cortensor Chatbot</p>
        {/* Add the reset button to the sidebar footer */}
        <ResetStorageButton />
      </div>
    </aside>
  );
};

export default Sidebar;