"use client";
import React, { useState, useRef, useEffect } from 'react';
import { Cpu, ChevronDown, Check } from 'lucide-react';

interface Model {
  id: string;
  name: string;
  description?: string;
}

interface ModelSelectorProps {
  models: Model[];
  selectedModel: Model | undefined;
  onSelectModel: (id: string) => void;
}

const ModelSelector: React.FC<ModelSelectorProps> = ({ models, selectedModel, onSelectModel }) => {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (!selectedModel) return null;

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-neutral-surface border border-neutral-border rounded-lg text-sm text-neutral-text-secondary hover:bg-neutral-surface-hover hover:text-neutral-text-primary transition-colors duration-150"
      >
        <Cpu size={16} />
        <span className="hidden sm:inline">{selectedModel.name}</span>
        <ChevronDown size={16} className={`transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full right-0 mt-2 w-64 bg-neutral-surface border border-neutral-border rounded-lg shadow-xl z-20 animate-menu-enter">
          <ul className="py-1">
            {models.map(model => (
              <li key={model.id}>
                <button
                  onClick={() => {
                    onSelectModel(model.id);
                    setIsOpen(false);
                  }}
                  className="w-full text-left flex items-center justify-between px-3 py-2 text-sm text-neutral-text-primary hover:bg-neutral-surface-hover"
                >
                  <div className="flex flex-col">
                    <span>{model.name}</span>
                    {model.description && (
                      <span className="text-xs text-neutral-text-secondary">{model.description}</span>
                    )}
                  </div>
                  {selectedModel.id === model.id && <Check size={16} className="text-brand-primary" />}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default ModelSelector;