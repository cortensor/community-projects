"use client";
import React, { useState, useRef, useEffect } from 'react';
import { Persona } from '@/hooks/usePersonas';
import { Bot, ChevronDown, Check } from 'lucide-react';

interface PersonaSelectorProps {
  personas: Persona[];
  selectedPersona: Persona | undefined;
  onSelectPersona: (id: string) => void;
}

const PersonaSelector: React.FC<PersonaSelectorProps> = ({ personas, selectedPersona, onSelectPersona }) => {
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

  if (!selectedPersona) return null;

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 bg-neutral-surface border border-neutral-border rounded-lg text-sm text-neutral-text-secondary hover:bg-neutral-surface-hover hover:text-neutral-text-primary transition-colors duration-150"
      >
        <Bot size={16} />
        <span>{selectedPersona.name}</span>
        <ChevronDown size={16} className={`transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full right-0 mt-2 w-56 bg-neutral-surface border border-neutral-border rounded-lg shadow-xl z-20 animate-menu-enter">
          <ul className="py-1">
            {personas.map(persona => (
              <li key={persona.id}>
                <button
                  onClick={() => {
                    onSelectPersona(persona.id);
                    setIsOpen(false);
                  }}
                  className="w-full text-left flex items-center justify-between px-3 py-2 text-sm text-neutral-text-primary hover:bg-neutral-surface-hover"
                >
                  <span>{persona.name}</span>
                  {selectedPersona.id === persona.id && <Check size={16} className="text-brand-primary" />}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default PersonaSelector;