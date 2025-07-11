"use client";
import React from 'react';
import { PlusCircle } from 'lucide-react';

interface NewChatButtonProps {
  isSidebarOpen: boolean;
  onNewChat: () => void;
}

const NewChatButton: React.FC<NewChatButtonProps> = ({ isSidebarOpen, onNewChat }) => {
  return (
    <div className="p-2">
      <button
        onClick={onNewChat}
        className={`w-full flex items-center p-3 rounded-md text-sm font-medium transition-colors duration-150 ${isSidebarOpen ? 'justify-start' : 'justify-center'} text-gray-100 hover:bg-yellow-500 hover:text-black cursor-pointer`}
        title="New Chat"
      >
        <PlusCircle size={isSidebarOpen ? 18 : 22} className={isSidebarOpen ? "mr-2.5 flex-shrink-0" : "flex-shrink-0"} />
        {isSidebarOpen && "New Chat"}
      </button>
    </div>
  );
};

export default NewChatButton;