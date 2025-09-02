"use client";
import React from 'react';
import { PlusCircle } from 'lucide-react';

interface NewChatButtonProps {
  isSidebarOpen: boolean;
  onNewChat: () => void;
}

const NewChatButton: React.FC<NewChatButtonProps> = ({ isSidebarOpen, onNewChat }) => {
  return (
    <div className="p-3">
      <button
        onClick={onNewChat}
        className={`w-full flex items-center p-3 rounded-xl bg-gradient-to-r from-blue-500/20 to-purple-600/20 backdrop-blur-sm border border-white/10 text-sm font-medium text-white hover:from-blue-500/30 hover:to-purple-600/30 hover:border-white/20 ${isSidebarOpen ? 'justify-start' : 'justify-center'}`}
        title="New Chat"
      >
        <PlusCircle size={isSidebarOpen ? 18 : 22} className={isSidebarOpen ? "mr-3 flex-shrink-0" : "flex-shrink-0"} />
        {isSidebarOpen && "New Chat"}
      </button>
    </div>
  );
};

export default NewChatButton;