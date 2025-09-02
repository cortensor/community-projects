"use client";

import { useCallback, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from './redux';
import {
  selectAllModels,
  selectAllDomains,
  selectAllPersonas,
  selectCurrentModel,
  selectCurrentDomain,
  selectCurrentPersona,
  selectIsMemoryEnabled,
  selectIsConfigLoading,
  selectAvailableModelsCount,
  selectAvailableDomainsCount,
  selectAvailablePersonasCount,
  selectModelsWithResearch,
  selectModelsWithDomains,
  selectIsConfigurationValid,
  selectConfigurationSummary,
  loadConfigurations,
  saveConfiguration,
  selectModel,
  selectDomain,
  selectPersona,
  toggleMemory,
  setMemoryEnabled,
  resetConfiguration,
} from '@/store/slices/configSlice';

export function useReduxConfig() {
  const dispatch = useAppDispatch();

  // Memoized selectors for collections
  const models = useAppSelector(selectAllModels);
  const domains = useAppSelector(selectAllDomains);
  const personas = useAppSelector(selectAllPersonas);

  // Current selections
  const currentModel = useAppSelector(selectCurrentModel);
  const currentDomain = useAppSelector(selectCurrentDomain);
  const currentPersona = useAppSelector(selectCurrentPersona);

  // State
  const isMemoryEnabled = useAppSelector(selectIsMemoryEnabled);
  const isLoading = useAppSelector(selectIsConfigLoading);

  // Derived data
  const modelsCount = useAppSelector(selectAvailableModelsCount);
  const domainsCount = useAppSelector(selectAvailableDomainsCount);
  const personasCount = useAppSelector(selectAvailablePersonasCount);
  const modelsWithResearch = useAppSelector(selectModelsWithResearch);
  const modelsWithDomains = useAppSelector(selectModelsWithDomains);
  const isConfigValid = useAppSelector(selectIsConfigurationValid);
  const configSummary = useAppSelector(selectConfigurationSummary);

  // Initialize configuration on mount
  useEffect(() => {
    if (models.length === 0 && !isLoading) {
      dispatch(loadConfigurations());
    }
  }, [dispatch, models.length, isLoading]);

  // Actions
  const handleSelectModel = useCallback((modelId: string) => {
    dispatch(selectModel(modelId));
  }, [dispatch]);

  const handleSelectDomain = useCallback((domainId: string) => {
    dispatch(selectDomain(domainId));
  }, [dispatch]);

  const handleSelectPersona = useCallback((personaId: string) => {
    dispatch(selectPersona(personaId));
  }, [dispatch]);

  const handleToggleMemory = useCallback(() => {
    dispatch(toggleMemory());
  }, [dispatch]);

  const handleSetMemoryEnabled = useCallback((enabled: boolean) => {
    dispatch(setMemoryEnabled(enabled));
  }, [dispatch]);

  const handleResetConfiguration = useCallback(() => {
    dispatch(resetConfiguration());
  }, [dispatch]);

  const handleSaveConfiguration = useCallback(() => {
    const config = {
      selectedModelId: currentModel?.id,
      selectedDomainId: currentDomain?.id,
      selectedPersonaId: currentPersona?.id,
      isMemoryEnabled,
    };
    dispatch(saveConfiguration(config));
  }, [dispatch, currentModel, currentDomain, currentPersona, isMemoryEnabled]);

  return {
    // Collections
    models,
    domains,
    personas,

    // Current selections
    currentModel,
    currentDomain,
    currentPersona,
    
    // State
    isMemoryEnabled,
    isLoading,
    
    // Derived data
    modelsCount,
    domainsCount,
    personasCount,
    modelsWithResearch,
    modelsWithDomains,
    isConfigValid,
    configSummary,

    // Actions
    selectModel: handleSelectModel,
    selectDomain: handleSelectDomain,
    selectPersona: handleSelectPersona,
    toggleMemory: handleToggleMemory,
    setMemoryEnabled: handleSetMemoryEnabled,
    resetConfiguration: handleResetConfiguration,
    saveConfiguration: handleSaveConfiguration,
  };
}