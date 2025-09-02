import { Message } from '@/types';

export interface PromptContext {
  messages: Message[];
  persona?: string;
  domainContext?: string;
  historySummary?: string;
  currentDate: string;
  modelId: string;
}

export interface PromptBuilder {
  buildPrompt(context: PromptContext): string;
  getModelId(): string;
  supportsResearch(): boolean;
  supportsDomains(): boolean;
}

export interface CompactHistoryConfig {
  maxLength: number;
  maxRecentMessages: number;
  includeTopics: boolean;
  topicKeywords: string[];
}

export interface PromptTemplateConfig {
  systemSection: string;
  historySection: string;
  currentMessageSection: string;
  responseFormat?: string;
  includeThinking?: boolean;
}