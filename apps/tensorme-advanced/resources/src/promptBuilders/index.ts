import { PromptBuilderFactory } from './builders/PromptBuilderFactory';

// Types
export type { 
  PromptContext, 
  PromptBuilder, 
  CompactHistoryConfig, 
  PromptTemplateConfig 
} from './types';

// Base classes
export { BasePromptBuilder } from './builders/BasePromptBuilder';

// Concrete implementations
export { LlavaPromptBuilder } from './builders/LlavaPromptBuilder';
export { DeepSeekPromptBuilder } from './builders/DeepSeekPromptBuilder';

// Factory
export { PromptBuilderFactory } from './builders/PromptBuilderFactory';

// Utility functions
export const createPromptContext = (
  messages: any[],
  modelId: string,
  persona?: string,
  domainContext?: string,
  historySummary?: string
) => ({
  messages,
  modelId,
  persona,
  domainContext,
  historySummary,
  currentDate: new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
});

export const buildPrompt = (
  messages: any[],
  modelId: string,
  persona?: string,
  domainContext?: string,
  historySummary?: string
): string => {
  const builder = PromptBuilderFactory.getBuilder(modelId);
  if (!builder) {
    throw new Error(`No prompt builder found for model: ${modelId}`);
  }

  const context = createPromptContext(messages, modelId, persona, domainContext, historySummary);
  return builder.buildPrompt(context);
};