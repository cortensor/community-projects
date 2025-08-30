"use client";

import { useState, useEffect } from 'react';
import { getFromLocalStorage, saveToLocalStorage } from '@/lib/localStorage';

export interface Persona {
  id: string;
  name: string;
  description: string;
}

const prebuiltPersonas: Persona[] = [
  { id: 'cortensor-default', name: 'Cortensor (Default)', description: 'a world-class AI assistant named Cortensor. Your persona is helpful, professional, and slightly witty.' },
  { id: 'sarcastic-bot', name: 'Sarcastic Bot', description: 'a sarcastic AI who gives begrudgingly helpful but witty answers.' },
  { id: 'shakespearean-bard', name: 'Shakespearean Bard', description: 'an AI who speaks in the style of William Shakespeare, using thou, thee, and thy.' },
  { id: 'pirate-captain', name: 'Pirate Captain', description: 'a salty pirate captain AI who answers with a hearty "Ahoy!" and sprinkles pirate slang in every response.' },
];

export const usePersonas = () => {
  const [personas, setPersonas] = useState<Persona[]>(prebuiltPersonas);
  const [selectedPersonaId, setSelectedPersonaId] = useState<string>('cortensor-default');

  useEffect(() => {
    const savedPersonaId = getFromLocalStorage<string | null>('selectedPersonaId', 'cortensor-default');
    if (savedPersonaId) {
      setSelectedPersonaId(savedPersonaId);
    }
  }, []);

  const handleSelectPersona = (id: string) => {
    setSelectedPersonaId(id);
    saveToLocalStorage('selectedPersonaId', id);
  };

  const selectedPersona = personas.find(p => p.id === selectedPersonaId);

  return {
    personas,
    selectedPersona,
    handleSelectPersona,
  };
};