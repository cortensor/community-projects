import { PromptServiceInterface, PromptBuildParams, StreamChunk, SingleShotResponse } from './types';
import { PromptBuilderFactory, createPromptContext } from '@/promptBuilders';

export class LlamaPromptService implements PromptServiceInterface {
  private static readonly MODEL_ID = 'llama-3.1-405b';
  
  buildPrompt({ messages, persona, domainContext, historySummary }: PromptBuildParams): string {
    const builder = PromptBuilderFactory.getBuilder(LlamaPromptService.MODEL_ID);
    
    if (!builder) {
      throw new Error(`No prompt builder found for model: ${LlamaPromptService.MODEL_ID}`);
    }
    
    const context = createPromptContext(
      messages,
      LlamaPromptService.MODEL_ID,
      persona,
      domainContext,
      historySummary
    );
    
    return builder.buildPrompt(context);
  }

  getSessionId(): number {
    return parseInt(process.env.CORTENSOR_LLAMA_SESSION_ID || '-1');
  }
}

export const llamaPromptService = new LlamaPromptService();