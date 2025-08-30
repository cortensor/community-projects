import { Message } from '@/types';

export interface PromptBuildParams {
  messages: Message[];
  persona?: string;
  domainContext?: string;
  historySummary?: string;
}

export interface StreamChunk {
  content: string;
  thinking?: string;
  title?: string;
  historySummary?: string;
  isThinking?: boolean;
  isComplete?: boolean;
}

export interface SingleShotResponse {
  content: string;
  thinking?: string;
  title?: string;
  historySummary?: string;
}

export interface PromptServiceInterface {
  buildPrompt(params: PromptBuildParams): string;
  getSessionId(): number;
}