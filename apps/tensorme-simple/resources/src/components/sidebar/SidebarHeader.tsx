"use client";
import React from 'react';
import { X, Menu } from 'lucide-react';

interface SidebarHeaderProps {
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
}

const SidebarHeader: React.FC<SidebarHeaderProps> = ({ isSidebarOpen, toggleSidebar }) => {
  return (
    <div className={`p-4 flex items-center ${isSidebarOpen ? 'justify-between' : 'justify-center'} h-16 border-b border-neutral-800`}>
      {isSidebarOpen && <h2 className="text-lg font-semibold text-gray-100">Chat History</h2>}
      <button onClick={toggleSidebar} className="md:hidden p-1 rounded-md text-gray-400 hover:text-gray-100 hover:bg-neutral-700 cursor-pointer transition-colors">
        {isSidebarOpen ? <X size={20} /> : <Menu size={20} />}
      </button>
    </div>
  );
};

export default SidebarHeader;