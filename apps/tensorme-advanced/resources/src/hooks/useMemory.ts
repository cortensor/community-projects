"use client";

import { useState, useEffect, useCallback } from 'react';
import { getFromLocalStorage, saveToLocalStorage } from '@/lib/localStorage';

export const useMemory = () => {
  const [isMemoryEnabled, setIsMemoryEnabled] = useState<boolean>(() => getFromLocalStorage('isMemoryEnabled', true));

  const toggleMemory = useCallback(() => {
    setIsMemoryEnabled(prev => {
      const newState = !prev;
      saveToLocalStorage('isMemoryEnabled', newState);
      return newState;
    });
  }, []);

  useEffect(() => {
    const savedState = getFromLocalStorage('isMemoryEnabled', true);
    setIsMemoryEnabled(savedState);
  }, []);


  return { isMemoryEnabled, toggleMemory };
};