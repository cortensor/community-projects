import axios from 'axios';
import type { ArticleContent } from './urlFetcher';

export interface SummaryResult {
  summary: string;
  keyPoints: string[];
  wordCount: number;
  needsEnrichment: boolean;
}

export interface EnrichmentSource {
  title: string;
  url: string;
  snippet: string;
}

export class CortensorService {
  private apiKey: string;
  private apiUrl: string;
  private sessionId: number;
  private promptType: number;
  private timeout: number;
  private precommitTimeout: number;
  private maxTokens: number;
  private temperature: number;
  private topP: number;
  private topK: number;
  private presencePenalty: number;
  private frequencyPenalty: number;
  private stream: boolean;

  constructor() {
    this.apiKey = process.env.CORTENSOR_API_KEY || '';
    
    // Use the standard API endpoint as per documentation
    const baseUrl = process.env.CORTENSOR_BASE_URL || 'http://69.164.253.134:5010';
    this.apiUrl = `${baseUrl}/api/v1/completions`;
    
    // Get session ID from environment variable
    this.sessionId = parseInt(process.env.CORTENSOR_SESSION || '6');
    this.promptType = parseInt(process.env.CORTENSOR_PROMPT_TYPE || '1');
    this.timeout = parseInt(process.env.CORTENSOR_TIMEOUT || '300');
    this.precommitTimeout = parseInt(process.env.CORTENSOR_PRECOMMIT_TIMEOUT || '90');
    this.maxTokens = parseInt(process.env.CORTENSOR_MAX_TOKENS || '6000');
    this.temperature = parseFloat(process.env.CORTENSOR_TEMPERATURE || '0.3');
    this.topP = parseFloat(process.env.CORTENSOR_TOP_P || '0.9');
    this.topK = parseInt(process.env.CORTENSOR_TOP_K || '40');
    this.presencePenalty = parseFloat(process.env.CORTENSOR_PRESENCE_PENALTY || '0');
    this.frequencyPenalty = parseFloat(process.env.CORTENSOR_FREQUENCY_PENALTY || '0');
    this.stream = process.env.CORTENSOR_STREAM === 'true';
    
    if (!this.apiKey) {
      throw new Error('CORTENSOR_API_KEY is required');
    }
  }

  async generateSummary(article: ArticleContent): Promise<SummaryResult> {
    try {
      const prompt = this.createSummaryPrompt(article);
      const clientReference = `summarize-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      
      const response = await axios.post(
        this.apiUrl,
        {
          session_id: this.sessionId, // Use session_id from environment variable
          prompt: prompt,
          stream: this.stream,
          timeout: this.timeout
        },
        {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json'
          }
        }
      );

      const summaryText = response.data.choices?.[0]?.text || response.data.text || '';
      
      // Parse the response to extract summary and key points
      const result = this.parseSummaryResponse(summaryText);
      
      // Check if summary needs enrichment
      result.needsEnrichment = this.shouldEnrich(result);
      
      return result;
      
    } catch (error) {
      console.error('Cortensor API error:', error);
      throw new Error('Failed to generate summary with Cortensor');
    }
  }

  async enrichSummary(
    originalSummary: SummaryResult,
    additionalSources: EnrichmentSource[]
  ): Promise<SummaryResult> {
    try {
      const prompt = this.createEnrichmentPrompt(originalSummary, additionalSources);
      const clientReference = `enrich-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      
      const response = await axios.post(
        this.apiUrl,
        {
          session_id: this.sessionId, // Use session_id from environment variable
          prompt: prompt,
          stream: this.stream,
          timeout: this.timeout
        },
        {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json'
          }
        }
      );

      const enrichedText = response.data.choices?.[0]?.text || response.data.text || '';
      const result = this.parseSummaryResponse(enrichedText);
      result.needsEnrichment = false; // Already enriched
      
      return result;
      
    } catch (error) {
      console.error('Summary enrichment error:', error);
      // Return original summary if enrichment fails
      return originalSummary;
    }
  }

  private createSummaryPrompt(article: ArticleContent): string {
    return `You are a professional research analyst. Analyze the following article and provide a clean, well-structured summary.

Title: ${article.title}
Source: ${article.url}
Content: ${article.content}

CRITICAL FORMATTING REQUIREMENTS:
- Write in clean, professional language
- NO special tokens, symbols, or artifacts
- NO section headers in your response
- Use natural paragraph breaks
- Write 3-4 focused paragraphs (2-3 sentences each)
- End with exactly 8 key insights using bullet points (•)

Please write your response in this exact format:

[First paragraph covering main topic and context]

[Second paragraph covering key findings and details]

[Third paragraph covering implications and significance]

[Fourth paragraph if needed for additional important points]

KEY INSIGHTS:
• [Insight 1]
• [Insight 2]
• [Insight 3]
• [Insight 4]
• [Insight 5]
• [Insight 6]
• [Insight 7]
• [Insight 8]

IMPORTANT: Write naturally without any special formatting, tokens, or artifacts. Keep paragraphs short and focused.
• [Detailed key insight 3]
• [Detailed key insight 4]
• [Detailed key insight 5]
• [Detailed key insight 6]

Begin your professional analysis now:`;
  }

  private createEnrichmentPrompt(
    originalSummary: SummaryResult,
    sources: EnrichmentSource[]
  ): string {
    const sourcesText = sources
      .map(source => `- ${source.title}\n  ${source.snippet}\n  Source: ${source.url}`)
      .join('\n\n');

    return `<thinking>
I need to enhance the existing summary by incorporating relevant information from additional sources. The goal is to create a more comprehensive and informative summary while maintaining clear structure and professional quality.
</thinking>

As an expert Research Summarizer AI, enhance the following summary by integrating relevant information from additional sources:

**ORIGINAL SUMMARY:**
${originalSummary.summary}

**ORIGINAL KEY INSIGHTS:**
${originalSummary.keyPoints.map(point => `• ${point}`).join('\n')}

**ADDITIONAL SOURCES:**
${sourcesText}

**ENHANCEMENT INSTRUCTIONS:**
Create an enhanced summary that:
- Incorporates relevant information from additional sources
- Maintains the structure and clarity of the original summary
- Adds depth and context where appropriate
- Ensures all information is well-integrated and coherent
- Expands the summary to 3-4 substantial paragraphs if beneficial
- Enhances key insights with additional context and supporting evidence

**QUALITY STANDARDS:**
- Use professional English throughout
- Maintain factual accuracy and objectivity
- Ensure seamless integration of new information
- Preserve the analytical depth of the original
- Add value through comprehensive coverage

**RESPONSE FORMAT:**
SUMMARY:
[Enhanced and comprehensive summary here]

KEY INSIGHTS:
• [Enhanced/expanded key insight 1]
• [Enhanced/expanded key insight 2]
• [Additional comprehensive insights as needed]

Begin summary enhancement:`;
  }

  private parseSummaryResponse(text: string): SummaryResult {
    // First, filter out DeepSeek thinking process
    let cleanedText = text;
    
    // Remove <think>...</think> blocks
    cleanedText = cleanedText.replace(/<think>[\s\S]*?<\/think>/gi, '');
    
    // If there's a </think> tag, take everything after it
    const thinkEndIndex = text.toLowerCase().lastIndexOf('</think>');
    if (thinkEndIndex !== -1) {
      cleanedText = text.substring(thinkEndIndex + 8).trim(); // 8 = length of '</think>'
    }
    
    // Clean all AI artifacts
    cleanedText = cleanedText
      .replace(/<｜end▁of▁sentence｜>/g, '')
      .replace(/\<\|end▁of▁sentence\|\>/g, '')
      .replace(/｜end▁of▁sentence｜/g, '')
      .replace(/end▁of▁sentence/g, '')
      .replace(/▁+/g, ' ')
      .replace(/▁/g, ' ')
      .replace(/\*\*([^*\n]+)\*\*/g, '$1') // Remove bold formatting
      .replace(/^\*\*\s*/gm, '')
      .replace(/\s*\*\*$/gm, '')
      .replace(/\s+/g, ' ')
      .trim();

    // Look for KEY INSIGHTS section with more flexible patterns
    const keyInsightsMatch = cleanedText.match(/\*\*KEY INSIGHTS?\*\*:?\s*([\s\S]*?)(?=\n\n|\*\*ADDITIONAL|$)/i) ||
                            cleanedText.match(/KEY INSIGHTS?\s*:?\s*([\s\S]*?)(?=\n\n|\*\*ADDITIONAL|$)/i);
    
    // Extract summary (everything before KEY INSIGHTS)
    let summary = cleanedText;
    if (keyInsightsMatch) {
      const keyInsightsIndex = cleanedText.toLowerCase().indexOf('key insights');
      if (keyInsightsIndex > 0) {
        summary = cleanedText.substring(0, keyInsightsIndex).trim();
      }
    }

    // Extract key points with improved parsing
    let keyPoints: string[] = [];
    if (keyInsightsMatch) {
      const keyInsightsText = keyInsightsMatch[1];
      
      // Split by bullet points first - look for • followed by text
      const bulletSplit = keyInsightsText.split(/\s*•\s*/).filter(part => part.trim().length > 10);
      
      if (bulletSplit.length > 1) {
        // Remove the first element if it's not a proper bullet point
        if (bulletSplit[0].trim().length < 50 || !bulletSplit[0].includes('.')) {
          bulletSplit.shift();
        }
        
        keyPoints = bulletSplit.map(point => {
          // Clean up each point
          return point.trim()
            .replace(/^\s*[\-\*•]\s*/, '') // Remove any remaining bullets
            .replace(/\s+/g, ' ') // Normalize whitespace
            .trim();
        }).filter(point => point.length > 15);
      } else {
        // Fallback: try other bullet patterns
        const bulletPoints = keyInsightsText.match(/(?:^|\n)[\s]*(?:[-•*]|\d+\.)\s*(.+)/gm);
        
        if (bulletPoints && bulletPoints.length > 0) {
          keyPoints = bulletPoints.map(point => 
            point.replace(/^[\s]*(?:[-•*]|\d+\.)\s*/, '').trim()
          ).filter(point => point.length > 10);
        } else {
          // If no bullet points, try splitting by sentences
          const sentences = keyInsightsText.split(/(?<=[.!?])\s+/).filter(s => s.trim().length > 20);
          if (sentences.length > 1) {
            keyPoints = sentences.map(s => s.trim()).filter(s => s.length > 0);
          }
        }
      }
    }

    // Clean summary further
    summary = summary
      .replace(/^(SUMMARY|Executive Summary)[\s:]*\n?/i, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim();

    return {
      summary,
      keyPoints,
      wordCount: summary.split(/\s+/).length,
      needsEnrichment: false
    };
  }

  private shouldEnrich(summary: SummaryResult): boolean {
    const minParagraphs = parseInt(process.env.MIN_SUMMARY_PARAGRAPHS || '3');
    const paragraphCount = summary.summary.split('\n\n').length;
    
    return (
      summary.wordCount < 200 || 
      paragraphCount < minParagraphs ||
      summary.keyPoints.length < 4
    );
  }
}