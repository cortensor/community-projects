import { Message } from '@/types';
import { PromptBuilder, PromptContext, CompactHistoryConfig } from '../types';

export abstract class BasePromptBuilder implements PromptBuilder {
  protected modelId: string;
  protected supportsResearchMode: boolean;
  protected supportsDomainsMode: boolean;

  constructor(modelId: string, supportsResearch: boolean = false, supportsDomains: boolean = false) {
    this.modelId = modelId;
    this.supportsResearchMode = supportsResearch;
    this.supportsDomainsMode = supportsDomains;
  }

  abstract buildPrompt(context: PromptContext): string;

  getModelId(): string {
    return this.modelId;
  }

  supportsResearch(): boolean {
    return this.supportsResearchMode;
  }

  supportsDomains(): boolean {
    return this.supportsDomainsMode;
  }

  protected createCompactHistory(messages: Message[], config: CompactHistoryConfig): string {
    const validMessages = messages.filter((msg) => !msg.isError && msg.content.trim() !== '');
    
    if (validMessages.length === 0) {
      return '(Starting new conversation)';
    }
    
    if (validMessages.length <= config.maxRecentMessages) {
      // If few messages, show them compactly
      return validMessages
        .map(msg => `${msg.role === 'user' ? 'U' : 'A'}: ${this.truncateText(msg.content, 100)}`)
        .join(' | ');
    } else {
      // If many messages, create a topic-based summary
      const recentMessages = validMessages.slice(-config.maxRecentMessages);
      const topics = config.includeTopics ? this.extractTopics(validMessages, config.topicKeywords) : [];
      
      const recentContext = recentMessages
        .map(msg => `${msg.role === 'user' ? 'U' : 'A'}: ${this.truncateText(msg.content, 80)}`)
        .join(' | ');
      
      const topicSummary = topics.length > 0 
        ? `Topics: ${topics.join(', ')} | Recent: ${recentContext}`
        : `Recent: ${recentContext}`;
      
      return this.truncateText(topicSummary, config.maxLength);
    }
  }

  protected extractTopics(messages: Message[], topicKeywords: string[]): string[] {
    const topics: Set<string> = new Set();
    
    const allText = messages
      .filter(msg => msg.role === 'user') // Focus on user questions
      .map(msg => msg.content.toLowerCase())
      .join(' ');
    
    topicKeywords.forEach(keyword => {
      if (allText.includes(keyword)) {
        topics.add(keyword);
      }
    });
    
    return Array.from(topics).slice(0, 3); // Max 3 topics
  }

  protected truncateText(text: string, maxLength: number): string {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - 3) + '...';
  }

  protected buildSystemContext(persona?: string, domainContext?: string): string {
    const personaInstruction = persona || 'Cortensor, a helpful AI assistant.';
    
    return domainContext && this.supportsDomains()
      ? `${personaInstruction}\n\nDomain Expertise:\n${domainContext}`
      : personaInstruction;
  }

  protected formatCurrentDate(): string {
    return new Date().toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  }
}