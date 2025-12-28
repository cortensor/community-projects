import { useState, useEffect } from 'react';

const SPLASH_SCREEN_KEY = 'cortigpt-splash-shown';

export const useSplashScreen = () => {
  const [showSplash, setShowSplash] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check localStorage for splash screen state
    // const hasShownSplash = localStorage.getItem(SPLASH_SCREEN_KEY);
    const hasShownSplash = false;
    
    if (!hasShownSplash) {
      setShowSplash(true);
    }
    
    setIsLoading(false);
  }, []);

  const hideSplash = () => {
    setShowSplash(false);
    localStorage.setItem(SPLASH_SCREEN_KEY, 'true');
  };

  return {
    showSplash,
    hideSplash,
    isLoading
  };
};
