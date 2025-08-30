"use client";
import React from 'react';
import { MessageSquare, Menu, X, BrainCircuit } from 'lucide-react';
import { ChatSession } from '@/types';
import PersonaSelector from './PersonaSelector';
import ModelSelector from './ModelSelector';
import DomainSelector from './DomainSelector';
import { Persona } from '@/hooks/usePersonas';
import { Model } from '@/hooks/useModels';
import { DomainConfig } from '@/lib/domains';
import { modelSupportsDomains } from '@/lib/models';

interface ChatHeaderProps {
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  currentChatId: string | null;
  chatSessions: ChatSession[];
  personas: Persona[];
  selectedPersona: Persona | undefined;
  onSelectPersona: (id: string) => void;
  models: Model[];
  selectedModel: Model | undefined;
  onSelectModel: (id: string) => void;
  isMemoryEnabled: boolean;
  onToggleMemory: () => void;
  domains: DomainConfig[];
  selectedDomain: DomainConfig | undefined;
  onSelectDomain: (id: string) => void;
}

const ChatHeader: React.FC<ChatHeaderProps> = ({
  isSidebarOpen,
  toggleSidebar,
  currentChatId,
  chatSessions,
  personas,
  selectedPersona,
  onSelectPersona,
  models,
  selectedModel,
  onSelectModel,
  isMemoryEnabled,
  onToggleMemory,
  domains,
  selectedDomain,
  onSelectDomain
}) => {
  const currentSession = chatSessions.find(s => s.id === currentChatId);
  const currentSessionName = currentSession?.name || "New Chat";
  const showDomains = modelSupportsDomains(selectedModel?.id);

  return (
    <header className="sticky top-0 left-0 right-0 z-20 backdrop-blur-xl bg-black/10 border-b border-white/10 h-16 flex items-center justify-between px-3 md:px-6 flex-shrink-0">
      <div className="flex items-center gap-2 md:gap-4 min-w-0">
        <button 
          onClick={toggleSidebar} 
          className="p-2 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10 text-white/70 hover:text-white hover:bg-white/10 block md:hidden"
        >
          {isSidebarOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
        <div className="flex items-center gap-3 min-w-0">
          <div className="p-2 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-600/20 backdrop-blur-sm border border-white/10">
            <MessageSquare size={20} className="text-blue-300" />
          </div>
          <h1 className="text-lg font-medium text-white/90 whitespace-nowrap overflow-x-scroll custom-scrollbar max-w-[160px] sm:max-w-[320px] md:max-w-[480px] lg:max-w-[640px] xl:max-w-[960px]">
            {currentSessionName}
          </h1>
        </div>
      </div>
      <div className="flex items-center gap-2 md:gap-3">
        {showDomains && (
          <DomainSelector
            domains={domains}
            selectedDomain={selectedDomain}
            onSelectDomain={onSelectDomain}
          />
        )}
        <button
          onClick={onToggleMemory}
          className={`relative flex items-center gap-2 px-3 py-2 backdrop-blur-sm border rounded-xl text-sm font-medium ${
            isMemoryEnabled 
              ? 'border-blue-400/30 text-blue-300 bg-blue-500/10' 
              : 'border-white/10 text-white/60 hover:bg-white/5 hover:text-white/80'
          }`}
          title={isMemoryEnabled ? 'Memory is ON' : 'Memory is OFF'}
        >
          <BrainCircuit size={16} />
          <span className="hidden md:inline">Memory</span>
          <div className="absolute -top-2 -right-2">
            <span className="text-[9px] font-bold bg-gradient-to-r from-orange-400 to-red-500 text-white px-1.5 py-0.5 rounded-full shadow-lg">
              EXP
            </span>
          </div>
        </button>
        <ModelSelector
          models={models}
          selectedModel={selectedModel}
          onSelectModel={onSelectModel}
        />
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