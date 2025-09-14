import { ClientPromptServiceInterface } from './types';
import { deepseekClientService } from './deepseekClientService';
import { llavaClientService } from './llavaClientService';
import { llamaClientService } from './llamaClientService';

const clientPromptServices: Record<string, ClientPromptServiceInterface> = {
  'deepseek-r1': deepseekClientService,
  'llava-v1': llavaClientService,
  'llama-3.1-405b': llamaClientService,
};

export function getClientPromptService(modelId: string): ClientPromptServiceInterface {
  const service = clientPromptServices[modelId];
  if (!service) {
    console.warn(`No client prompt service found for model: ${modelId}, falling back to deepseek`);
    return deepseekClientService;
  }
  return service;
}

export * from './types';
export { deepseekClientService } from './deepseekClientService';
export { llavaClientService } from './llavaClientService';
export { llamaClientService } from './llamaClientService';