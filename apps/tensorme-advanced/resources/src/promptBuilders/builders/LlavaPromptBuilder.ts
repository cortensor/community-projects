import { BasePromptBuilder } from './BasePromptBuilder';
import { PromptContext, CompactHistoryConfig } from '../types';

export class LlavaPromptBuilder extends BasePromptBuilder {
  private static readonly TOPIC_KEYWORDS = [
    'investment', 'stock', 'finance', 'money', 'trading', 'crypto',
    'programming', 'code', 'development', 'software', 'tech',
    'health', 'fitness', 'medical', 'diet', 'exercise',
    'education', 'learning', 'study', 'research', 'analysis',
    'business', 'marketing', 'strategy', 'management',
    'travel', 'culture', 'language', 'history', 'science'
  ];

  private static readonly COMPACT_HISTORY_CONFIG: CompactHistoryConfig = {
    maxLength: 300,
    maxRecentMessages: 4,
    includeTopics: true,
    topicKeywords: LlavaPromptBuilder.TOPIC_KEYWORDS
  };

  constructor() {
    super('llava-v1', false, false); // LLaVA doesn't support research or domains
  }

  buildPrompt(context: PromptContext): string {
    const systemContext = this.buildSystemContext(context.persona, context.domainContext);
    const historyMessages = context.messages.slice(0, -1);
    
    // Create compact history for LLaVA - only essential context
    let compactHistory: string;
    
    if (context.historySummary && context.historySummary.trim() !== '') {
      // Use existing summary if available
      compactHistory = context.historySummary;
    } else if (historyMessages.length === 0) {
      // No history
      compactHistory = '(Starting new conversation)';
    } else {
      // Create compact history from recent messages
      compactHistory = this.createCompactHistory(historyMessages, LlavaPromptBuilder.COMPACT_HISTORY_CONFIG);
    }
    
    const currentUserMessage = context.messages[context.messages.length - 1];
    
    return `You are ${systemContext}. Today is ${context.currentDate}.

Context: ${compactHistory}

User: ${currentUserMessage.content}

Respond in this exact format:
Title: 
Answer: 
Summary: `;
  }
}