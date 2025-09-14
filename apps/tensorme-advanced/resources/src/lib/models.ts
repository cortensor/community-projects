export interface ModelConfig {
  id: string;
  name: string;
  description: string;
  supportsResearch?: boolean;
  supportsDomains?: boolean;
}

export const AVAILABLE_MODELS: ModelConfig[] = [
  {
    id: 'llava-v1',
    name: 'LLaVA',
    description: 'Faster responses, lighter reasoning',
    supportsResearch: false,
    supportsDomains: false
  },
  {
    id: 'deepseek-r1',
    name: 'DeepSeek R1',
    description: 'Advanced reasoning model',
    supportsResearch: true,
    supportsDomains: true
  },
  {
    id: 'llama-3.1-405b',
    name: 'Llama 3.1 405B',
    description: 'Large language model with strong reasoning capabilities',
    supportsResearch: true,
    supportsDomains: true
  }
];

export const getModelConfig = (modelId: string): ModelConfig | undefined => {
  return AVAILABLE_MODELS.find(model => model.id === modelId);
};

export const getClientModels = () => {
  return AVAILABLE_MODELS.map(({ id, name, description, supportsResearch, supportsDomains }) => ({
    id,
    name,
    description,
    supportsResearch,
    supportsDomains
  }));
};

/**
 * Check if a model supports research mode
 */
export const modelSupportsResearch = (modelId?: string): boolean => {
  if (!modelId) return false;
  const model = getModelConfig(modelId);
  return model?.supportsResearch || false;
};

/**
 * Check if a model supports domain specialization
 */
export const modelSupportsDomains = (modelId?: string): boolean => {
  if (!modelId) return false;
  const model = getModelConfig(modelId);
  return model?.supportsDomains || false;
};