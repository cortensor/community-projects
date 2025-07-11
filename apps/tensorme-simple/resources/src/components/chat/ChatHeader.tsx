"use client";
import React from 'react';
import { MessageSquare, Menu, X, BrainCircuit } from 'lucide-react';
import { ChatSession } from '@/types';
import PersonaSelector from './PersonaSelector';
import { Persona } from '@/hooks/usePersonas';

interface ChatHeaderProps {
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  currentChatId: string | null;
  chatSessions: ChatSession[];
  personas: Persona[];
  selectedPersona: Persona | undefined;
  onSelectPersona: (id: string) => void;
  isMemoryEnabled: boolean;
  onToggleMemory: () => void;
}

const ChatHeader: React.FC<ChatHeaderProps> = ({
  isSidebarOpen,
  toggleSidebar,
  currentChatId,
  chatSessions,
  personas,
  selectedPersona,
  onSelectPersona,
  isMemoryEnabled,
  onToggleMemory
}) => {
  const currentSessionName = chatSessions.find(s => s.id === currentChatId)?.name || "New Chat";

  return (
    <header className="bg-neutral-surface h-16 shadow-sm flex items-center justify-between px-2 md:px-4 border-b border-neutral-border flex-shrink-0">
      <div className="flex items-center gap-1 md:gap-3 min-w-0">
        <button onClick={toggleSidebar} className="p-1 rounded-md text-neutral-text-secondary hover:text-neutral-text-primary block md:hidden cursor-pointer transition-colors">
          {isSidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
        <div className="flex items-center gap-2 min-w-0">
          <MessageSquare size={22} className="text-brand-primary flex-shrink-0" />
          <h1 className="text-lg font-medium text-neutral-text-primary truncate">
            {currentSessionName}
          </h1>
        </div>
      </div>
      <div className="flex items-center gap-2 md:gap-3">
        <button
          onClick={onToggleMemory}
          className={`relative flex items-center gap-2 px-2 md:px-3 py-1.5 border rounded-lg text-sm transition-all duration-200 ${isMemoryEnabled ? 'border-brand-primary text-brand-primary bg-brand-primary/10' : 'border-neutral-border text-neutral-text-secondary hover:bg-neutral-surface-hover'
            }`}
          title={isMemoryEnabled ? 'Memory is ON' : 'Memory is OFF'}
        >
          <BrainCircuit size={16} />
          <span className="hidden md:inline">Memory</span>
          <div className="absolute -top-1.5 -right-1.5">
            <span className="text-[9px] font-semibold bg-red-500 text-white px-1.5 py-0.5 rounded-full">
              EXP
            </span>
          </div>
        </button>
        <PersonaSelector
          personas={personas}
          selectedPersona={selectedPersona}
          onSelectPersona={onSelectPersona}
        />
      </div>
    </header>
  );
};

export default ChatHeader;