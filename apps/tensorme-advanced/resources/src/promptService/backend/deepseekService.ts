import { PromptServiceInterface, PromptBuildParams, StreamChunk, SingleShotResponse } from './types';
import { PromptBuilderFactory, createPromptContext } from '@/promptBuilders';

export class DeepSeekPromptService implements PromptServiceInterface {
  private static readonly MODEL_ID = 'deepseek-r1';
  
  buildPrompt({ messages, persona, domainContext, historySummary }: PromptBuildParams): string {
    const builder = PromptBuilderFactory.getBuilder(DeepSeekPromptService.MODEL_ID);
    
    if (!builder) {
      throw new Error(`No prompt builder found for model: ${DeepSeekPromptService.MODEL_ID}`);
    }
    
    const context = createPromptContext(
      messages,
      DeepSeekPromptService.MODEL_ID,
      persona,
      domainContext,
      historySummary
    );
    
    return builder.buildPrompt(context);
  }

  getSessionId(): number {
    return parseInt(process.env.CORTENSOR_DEEPSEEK_SESSION_ID || '-1');
  }
}

export const deepseekPromptService = new DeepSeekPromptService();