import { createSlice, PayloadAction, createAsyncThunk } from '@reduxjs/toolkit';
import { createSelector } from 'reselect';
import { DomainConfig } from '@/lib/domains';
import { ModelConfig } from '@/lib/models';
import { PersonaConfig } from '@/types';

interface ConfigState {
  selectedModelId: string;
  selectedDomainId: string;
  selectedPersonaId: string;
  isMemoryEnabled: boolean;
  models: ModelConfig[];
  domains: DomainConfig[];
  personas: PersonaConfig[];
  isLoading: boolean;
}

const initialState: ConfigState = {
  selectedModelId: 'deepseek-r1',
  selectedDomainId: 'general',
  selectedPersonaId: 'default',
  isMemoryEnabled: false,
  models: [],
  domains: [],
  personas: [],
  isLoading: false,
};

// Async thunks
export const loadConfigurations = createAsyncThunk(
  'config/loadConfigurations',
  async () => {
    try {
      // Load models
      const { AVAILABLE_MODELS } = await import('@/lib/models');
      const { DOMAIN_CONFIGS } = await import('@/lib/domains');
      
      // Load personas (you'll need to create this)
      const personas: PersonaConfig[] = [
        {
          id: 'default',
          name: 'Default',
          description: 'Cortensor, a world-class AI assistant: helpful, professional, and subtly witty.',
        },
        {
          id: 'professional',
          name: 'Professional',
          description: 'A formal, business-oriented assistant focused on efficiency and clarity.',
        },
        {
          id: 'friendly',
          name: 'Friendly',
          description: 'A warm, approachable assistant that communicates in a casual, friendly manner.',
        },
      ];

      // Load saved selections from localStorage
      const savedConfig = localStorage.getItem('app_config');
      const config = savedConfig ? JSON.parse(savedConfig) : {};

      return {
        models: AVAILABLE_MODELS,
        domains: DOMAIN_CONFIGS,
        personas,
        selectedModelId: config.selectedModelId || initialState.selectedModelId,
        selectedDomainId: config.selectedDomainId || initialState.selectedDomainId,
        selectedPersonaId: config.selectedPersonaId || initialState.selectedPersonaId,
        isMemoryEnabled: config.isMemoryEnabled || initialState.isMemoryEnabled,
      };
    } catch (error) {
      throw new Error('Failed to load configurations');
    }
  }
);

export const saveConfiguration = createAsyncThunk(
  'config/saveConfiguration',
  async (config: Partial<Pick<ConfigState, 'selectedModelId' | 'selectedDomainId' | 'selectedPersonaId' | 'isMemoryEnabled'>>) => {
    const currentConfig = JSON.parse(localStorage.getItem('app_config') || '{}');
    const updatedConfig = { ...currentConfig, ...config };
    localStorage.setItem('app_config', JSON.stringify(updatedConfig));
    return config;
  }
);

const configSlice = createSlice({
  name: 'config',
  initialState,
  reducers: {
    selectModel: (state, action: PayloadAction<string>) => {
      state.selectedModelId = action.payload;
      // Auto-save configuration
      const config = {
        selectedModelId: action.payload,
        selectedDomainId: state.selectedDomainId,
        selectedPersonaId: state.selectedPersonaId,
        isMemoryEnabled: state.isMemoryEnabled,
      };
      localStorage.setItem('app_config', JSON.stringify(config));
    },

    selectDomain: (state, action: PayloadAction<string>) => {
      state.selectedDomainId = action.payload;
      // Auto-save configuration
      const config = {
        selectedModelId: state.selectedModelId,
        selectedDomainId: action.payload,
        selectedPersonaId: state.selectedPersonaId,
        isMemoryEnabled: state.isMemoryEnabled,
      };
      localStorage.setItem('app_config', JSON.stringify(config));
    },

    selectPersona: (state, action: PayloadAction<string>) => {
      state.selectedPersonaId = action.payload;
      // Auto-save configuration
      const config = {
        selectedModelId: state.selectedModelId,
        selectedDomainId: state.selectedDomainId,
        selectedPersonaId: action.payload,
        isMemoryEnabled: state.isMemoryEnabled,
      };
      localStorage.setItem('app_config', JSON.stringify(config));
    },

    toggleMemory: (state) => {
      state.isMemoryEnabled = !state.isMemoryEnabled;
      // Auto-save configuration
      const config = {
        selectedModelId: state.selectedModelId,
        selectedDomainId: state.selectedDomainId,
        selectedPersonaId: state.selectedPersonaId,
        isMemoryEnabled: state.isMemoryEnabled,
      };
      localStorage.setItem('app_config', JSON.stringify(config));
    },

    setMemoryEnabled: (state, action: PayloadAction<boolean>) => {
      state.isMemoryEnabled = action.payload;
      // Auto-save configuration
      const config = {
        selectedModelId: state.selectedModelId,
        selectedDomainId: state.selectedDomainId,
        selectedPersonaId: state.selectedPersonaId,
        isMemoryEnabled: action.payload,
      };
      localStorage.setItem('app_config', JSON.stringify(config));
    },

    resetConfiguration: (state) => {
      state.selectedModelId = initialState.selectedModelId;
      state.selectedDomainId = initialState.selectedDomainId;
      state.selectedPersonaId = initialState.selectedPersonaId;
      state.isMemoryEnabled = initialState.isMemoryEnabled;
      localStorage.removeItem('app_config');
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loadConfigurations.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(loadConfigurations.fulfilled, (state, action) => {
        state.isLoading = false;
        state.models = action.payload.models;
        state.domains = action.payload.domains;
        state.personas = action.payload.personas;
        state.selectedModelId = action.payload.selectedModelId;
        state.selectedDomainId = action.payload.selectedDomainId;
        state.selectedPersonaId = action.payload.selectedPersonaId;
        state.isMemoryEnabled = action.payload.isMemoryEnabled;
      })
      .addCase(loadConfigurations.rejected, (state) => {
        state.isLoading = false;
        // Keep default values
      })
      .addCase(saveConfiguration.fulfilled, (state, action) => {
        Object.assign(state, action.payload);
      });
  },
});

export const {
  selectModel,
  selectDomain,
  selectPersona,
  toggleMemory,
  setMemoryEnabled,
  resetConfiguration,
} = configSlice.actions;

export default configSlice.reducer;

// Basic selectors (input selectors)
const selectConfigState = (state: { config: ConfigState }) => state.config;
const selectModels = (state: { config: ConfigState }) => state.config.models;
const selectDomains = (state: { config: ConfigState }) => state.config.domains;
const selectPersonas = (state: { config: ConfigState }) => state.config.personas;
const selectSelectedModelId = (state: { config: ConfigState }) => state.config.selectedModelId;
const selectSelectedDomainId = (state: { config: ConfigState }) => state.config.selectedDomainId;
const selectSelectedPersonaId = (state: { config: ConfigState }) => state.config.selectedPersonaId;

// Memoized selectors for derived data
export const selectAllModels = createSelector(
  [selectModels],
  (models) => models
);

export const selectAllDomains = createSelector(
  [selectDomains],
  (domains) => domains
);

export const selectAllPersonas = createSelector(
  [selectPersonas],
  (personas) => personas
);

export const selectCurrentModel = createSelector(
  [selectModels, selectSelectedModelId],
  (models, selectedId) => models.find(model => model.id === selectedId)
);

export const selectCurrentDomain = createSelector(
  [selectDomains, selectSelectedDomainId],
  (domains, selectedId) => domains.find(domain => domain.id === selectedId)
);

export const selectCurrentPersona = createSelector(
  [selectPersonas, selectSelectedPersonaId],
  (personas, selectedId) => personas.find(persona => persona.id === selectedId)
);

export const selectIsMemoryEnabled = createSelector(
  [selectConfigState],
  (config) => config.isMemoryEnabled
);

export const selectIsConfigLoading = createSelector(
  [selectConfigState],
  (config) => config.isLoading
);

// Complex derived selectors
export const selectAvailableModelsCount = createSelector(
  [selectAllModels],
  (models) => models.length
);

export const selectAvailableDomainsCount = createSelector(
  [selectAllDomains],
  (domains) => domains.length
);

export const selectAvailablePersonasCount = createSelector(
  [selectAllPersonas],
  (personas) => personas.length
);

// Model-specific derived selectors
export const selectModelsWithResearch = createSelector(
  [selectAllModels],
  (models) => models.filter(model => model.supportsResearch)
);

export const selectModelsWithDomains = createSelector(
  [selectAllModels],
  (models) => models.filter(model => model.supportsDomains)
);

// Configuration validation selectors
export const selectIsConfigurationValid = createSelector(
  [selectCurrentModel, selectCurrentDomain, selectCurrentPersona],
  (model, domain, persona) => !!(model && domain && persona)
);

export const selectConfigurationSummary = createSelector(
  [selectCurrentModel, selectCurrentDomain, selectCurrentPersona, selectIsMemoryEnabled],
  (model, domain, persona, memoryEnabled) => ({
    model: model?.name || 'Unknown',
    domain: domain?.name || 'Unknown',
    persona: persona?.name || 'Unknown',
    memoryEnabled,
  })
);