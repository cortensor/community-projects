import { ClientPromptServiceInterface, StreamChunk, SingleShotResponse } from './types';

export class LlavaClientService implements ClientPromptServiceInterface {
  parseStreamChunk(data: any): StreamChunk | null {
    try {
      if (!data.choices?.[0]?.text) return null;
      
      const textChunk = data.choices[0].text;
      
      // Parse the accumulated text to identify sections
      const sections = this.parsePlainTextSections(textChunk);
      
      // Determine what content to show based on what sections exist
      let displayContent = textChunk; // Default to showing everything
      let thinking = sections.thinking;
      let isThinking = false;
      
      // If we have structured sections, use them appropriately
      if (sections.answer) {
        // We have an answer section, show it as main content
        displayContent = sections.answer;
      } else if (sections.thinking && !sections.answer) {
        // Only thinking, no answer yet - we're in thinking phase
        isThinking = true;
        displayContent = ''; // Don't show thinking as main content
      }
      
      return {
        content: displayContent,
        thinking: thinking,
        title: sections.title,
        historySummary: sections.historySummary || sections.summary,
        isThinking: isThinking,
        isComplete: data.choices[0].finish_reason === 'stop'
      };
    } catch (error) {
      console.error('Error parsing LLaVA stream chunk:', error);
      return null;
    }
  }

  parseSingleShot(data: any): SingleShotResponse | null {
    try {
      if (!data.choices?.[0]?.text) return null;
      
      const fullText = data.choices[0].text;
      
      // Parse plain text structured response
      const sections = this.parsePlainTextSections(fullText);
      
      return {
        content: sections.answer || fullText,
        thinking: sections.thinking,
        title: sections.title,
        historySummary: sections.historySummary
      };
    } catch (error) {
      console.error('Error parsing LLaVA single shot response:', error);
      return null;
    }
  }

  private parsePlainTextSections(text: string) {
    const sections: Record<string, string> = {};
    
    // Split by section headers - updated to handle all possible sections
    const thinkingMatch = text.match(/Thinking:\s*([\s\S]*?)(?=\n(?:Title|Answer|Summary|History Summary):|$)/i);
    const titleMatch = text.match(/Title:\s*([\s\S]*?)(?=\n(?:Answer|Summary|History Summary):|$)/i);
    const answerMatch = text.match(/Answer:\s*([\s\S]*?)(?=\n(?:Summary|History Summary):|$)/i);
    const summaryMatch = text.match(/Summary:\s*([\s\S]*?)(?=\n(?:History Summary):|$)/i);
    const historyMatch = text.match(/History Summary:\s*([\s\S]*?)$/i);
    
    if (thinkingMatch) sections.thinking = thinkingMatch[1].trim();
    if (titleMatch) sections.title = titleMatch[1].trim();
    if (answerMatch) sections.answer = answerMatch[1].trim();
    if (summaryMatch) sections.summary = summaryMatch[1].trim();
    if (historyMatch) sections.historySummary = historyMatch[1].trim();
    
    return sections;
  }
}

export const llavaClientService = new LlavaClientService();