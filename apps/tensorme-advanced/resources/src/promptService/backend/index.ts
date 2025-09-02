import { PromptServiceInterface } from './types';
import { deepseekPromptService } from './deepseekService';
import { llavaPromptService } from './llavaService';
import { llamaPromptService } from './llamaService';

const promptServices: Record<string, PromptServiceInterface> = {
  'deepseek-r1': deepseekPromptService,
  'llava-v1': llavaPromptService,
  'llama-3.1-405b': llamaPromptService
};

export function getPromptService(modelId: string): PromptServiceInterface {
  const service = promptServices[modelId];
  if (!service) {
    console.warn(`No prompt service found for model: ${modelId}, falling back to deepseek`);
    return deepseekPromptService;
  }
  return service;
}

export * from './types';
export { deepseekPromptService } from './deepseekService';
export { llavaPromptService } from './llavaService';
export { llamaPromptService } from './llamaService';