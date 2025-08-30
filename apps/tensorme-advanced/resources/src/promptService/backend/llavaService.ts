import { PromptServiceInterface, PromptBuildParams, StreamChunk, SingleShotResponse } from './types';
import { PromptBuilderFactory, createPromptContext } from '@/promptBuilders';

export class LlavaPromptService implements PromptServiceInterface {
  private static readonly MODEL_ID = 'llava-v1';
  
  buildPrompt({ messages, persona, domainContext, historySummary }: PromptBuildParams): string {
    const builder = PromptBuilderFactory.getBuilder(LlavaPromptService.MODEL_ID);
    
    if (!builder) {
      throw new Error(`No prompt builder found for model: ${LlavaPromptService.MODEL_ID}`);
    }
    
    const context = createPromptContext(
      messages,
      LlavaPromptService.MODEL_ID,
      persona,
      domainContext,
      historySummary
    );
    
    return builder.buildPrompt(context);
  }

  getSessionId(): number {
    return parseInt(process.env.CORTENSOR_LLAVA_SESSION_ID || '-1');
  }
}

export const llavaPromptService = new LlavaPromptService();