import { ClientPromptServiceInterface, StreamChunk, SingleShotResponse } from './types';

export class DeepSeekClientService implements ClientPromptServiceInterface {
  parseStreamChunk(data: any): StreamChunk | null {
    try {
      if (!data.choices?.[0]?.text) return null;
      
      const textChunk = data.choices[0].text;
      
      // Parse sections from the stream response
      const sections = this.parseSections(textChunk);
      
      return {
        content: sections.answer || textChunk,
        thinking: sections.thinking,
        title: sections.title,
        historySummary: sections.historySummary,
        isThinking: !!sections.thinking && !sections.answer,
        isComplete: data.choices[0].finish_reason === 'stop'
      };
    } catch (error) {
      console.error('Error parsing DeepSeek stream chunk:', error);
      return null;
    }
  }

  parseSingleShot(data: any): SingleShotResponse | null {
    try {
      if (!data.choices?.[0]?.text) return null;
      
      const fullText = data.choices[0].text;
      const sections = this.parseSections(fullText);
      
      return {
        content: sections.answer || sections.cleanText || fullText,
        thinking: sections.thinking,
        title: sections.title,
        historySummary: sections.historySummary
      };
    } catch (error) {
      console.error('Error parsing DeepSeek single shot response:', error);
      return null;
    }
  }

  private parseSections(text: string): {
    thinking?: string;
    title?: string;
    answer?: string;
    historySummary?: string;
    cleanText?: string;
  } {
    const sections: any = {};
    
    // Handle the specific DeepSeek stream format with </think> tag
    const thinkSplit = text.split('</think>');
    
    if (thinkSplit.length > 1) {
      // Content before </think> is internal reasoning
      const internalThinking = thinkSplit[0].trim();
      const structuredContent = thinkSplit[1].trim();
      
      // Parse structured sections after </think>
      this.parseStructuredSections(structuredContent, sections);
      
      // If no structured thinking section, use internal thinking
      if (!sections.thinking && internalThinking) {
        sections.thinking = internalThinking;
      }
    } else {
      // No </think> tag, parse as structured content directly
      this.parseStructuredSections(text, sections);
    }
    
    // Legacy DeepSeek thinking tokens fallback
    if (!sections.thinking && !sections.answer) {
      const legacyThinkingMatch = text.match(/<｜begin of thinking｜>([\s\S]*?)<｜end of thinking｜>/);
      if (legacyThinkingMatch) {
        sections.thinking = legacyThinkingMatch[1].trim();
        sections.cleanText = text
          .replace(/<｜begin of thinking｜>[\s\S]*?<｜end of thinking｜>/g, '')
          .replace(/<｜thinking｜>[\s\S]*?<｜\/thinking｜>/g, '')
          .trim();
      }
    }
    
    // Final fallback: if no sections found, treat as answer
    if (!sections.thinking && !sections.answer && !sections.title) {
      sections.answer = text.trim();
    }
    
    return sections;
  }

  private parseStructuredSections(text: string, sections: any): void {
    // Parse "Thinking:" section (handles the specific format from the stream)
    const thinkingMatch = text.match(/Thinking:\s*([\s\S]*?)(?=\n\n(?:Title:|Answer:|History Summary:|Chat History:)|$)/i);
    if (thinkingMatch) {
      sections.thinking = thinkingMatch[1].trim();
    }
    
    // Parse "Title:" section
    const titleMatch = text.match(/Title:\s*([\s\S]*?)(?=\n\n(?:Answer:|History Summary:|Chat History:)|$)/i);
    if (titleMatch) {
      sections.title = titleMatch[1].trim();
    }
    
    // Parse "Answer:" section
    const answerMatch = text.match(/Answer:\s*([\s\S]*?)(?=\n\n(?:History Summary:|Chat History:)|$)/i);
    if (answerMatch) {
      sections.answer = answerMatch[1].trim();
    }
    
    // Parse "History Summary:" section
    const historySummaryMatch = text.match(/History Summary:\s*([\s\S]*?)(?=\n\n(?:Chat History:)|$)/i);
    if (historySummaryMatch) {
      sections.historySummary = historySummaryMatch[1].trim();
    }
  }
}

export const deepseekClientService = new DeepSeekClientService();