"use client";

import { useCallback, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from './redux';
import {
  selectUser,
  selectUserId,
  selectUserAddress,
  selectIsConnected,
  selectPreferences,
  selectIsUserLoading,
  selectIsUserInitialized,
  selectCanConnectWallet,
  selectTheme,
  selectFontSize,
  selectSoundEnabled,
  selectAutoSave,
  initializeUser,
  connectWallet,
  savePreferences,
  setUser,
  disconnect,
  updatePreferences,
  clearUser,
} from '@/store/slices/userSlice';

export function useReduxUser() {
  const dispatch = useAppDispatch();

  // Memoized selectors
  const user = useAppSelector(selectUser);
  const userId = useAppSelector(selectUserId);
  const address = useAppSelector(selectUserAddress);
  const isConnected = useAppSelector(selectIsConnected);
  const preferences = useAppSelector(selectPreferences);
  const isLoading = useAppSelector(selectIsUserLoading);
  const isInitialized = useAppSelector(selectIsUserInitialized);
  const canConnectWallet = useAppSelector(selectCanConnectWallet);

  // Individual preference selectors
  const theme = useAppSelector(selectTheme);
  const fontSize = useAppSelector(selectFontSize);
  const soundEnabled = useAppSelector(selectSoundEnabled);
  const autoSave = useAppSelector(selectAutoSave);

  // Initialize user on mount
  useEffect(() => {
    if (!isInitialized && !isLoading) {
      dispatch(initializeUser());
    }
  }, [dispatch, isInitialized, isLoading]);

  // Actions
  const handleConnectWallet = useCallback(() => {
    if (canConnectWallet) {
      dispatch(connectWallet());
    }
  }, [dispatch, canConnectWallet]);

  const handleDisconnect = useCallback(() => {
    dispatch(disconnect());
  }, [dispatch]);

  const handleUpdatePreferences = useCallback(
    (newPreferences: Partial<typeof preferences>) => {
      dispatch(updatePreferences(newPreferences));
      dispatch(savePreferences(newPreferences));
    },
    [dispatch, preferences]
  );

  const handleSetUser = useCallback(
    (userData: { userId: string; address?: string }) => {
      dispatch(setUser(userData));
    },
    [dispatch]
  );

  const handleClearUser = useCallback(() => {
    dispatch(clearUser());
  }, [dispatch]);

  return {
    // State
    user,
    userId,
    address,
    isConnected,
    preferences,
    isLoading,
    isInitialized,
    canConnectWallet,
    
    // Individual preferences
    theme,
    fontSize,
    soundEnabled,
    autoSave,

    // Actions
    connectWallet: handleConnectWallet,
    disconnect: handleDisconnect,
    updatePreferences: handleUpdatePreferences,
    setUser: handleSetUser,
    clearUser: handleClearUser,
  };
}