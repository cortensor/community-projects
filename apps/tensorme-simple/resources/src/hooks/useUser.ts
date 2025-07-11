"use client";

import { useState, useEffect } from 'react';
import { generateId } from '@/lib/utils';
import { getFromLocalStorage, saveToLocalStorage } from '@/lib/localStorage';

export const useUser = () => {
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    let storedUserId = getFromLocalStorage<string | null>('userId', null);
    if (!storedUserId) {
      storedUserId = generateId();
      saveToLocalStorage('userId', storedUserId);
    }
    setUserId(storedUserId);
  }, []);

  return { userId };
};