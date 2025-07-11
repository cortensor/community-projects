"use client";

import { useState, useEffect, useCallback } from 'react';
import { getFromLocalStorage, saveToLocalStorage } from '@/lib/localStorage';

export const useMemory = () => {
  // Default memory to enabled
  const [isMemoryEnabled, setIsMemoryEnabled] = useState<boolean>(() => getFromLocalStorage('isMemoryEnabled', true));

  const toggleMemory = useCallback(() => {
    setIsMemoryEnabled(prev => {
      const newState = !prev;
      saveToLocalStorage('isMemoryEnabled', newState);
      return newState;
    });
  }, []);

  useEffect(() => {
    // This effect ensures the state is correctly initialized on the client-side
    const savedState = getFromLocalStorage('isMemoryEnabled', true);
    setIsMemoryEnabled(savedState);
  }, []);


  return { isMemoryEnabled, toggleMemory };
};