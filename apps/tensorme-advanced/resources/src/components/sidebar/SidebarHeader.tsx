"use client";
import React from 'react';
import { X, Menu } from 'lucide-react';

interface SidebarHeaderProps {
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
}

const SidebarHeader: React.FC<SidebarHeaderProps> = ({ isSidebarOpen, toggleSidebar }) => {
  return (
    <div className={`p-4 flex items-center ${isSidebarOpen ? 'justify-between' : 'justify-center'} h-16 border-b border-white/10`}>
      {isSidebarOpen && <h2 className="text-lg font-semibold text-white/90">Chat History</h2>}
      <button onClick={toggleSidebar} className="md:hidden p-2 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10 text-white/60 hover:text-white hover:bg-white/10">
        {isSidebarOpen ? <X size={18} /> : <Menu size={18} />}
      </button>
    </div>
  );
};

export default SidebarHeader;