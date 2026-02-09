import axios from 'axios';
import type { ArticleContent } from './urlFetcher';
import { env, debugLog } from './env';

export interface SummaryResult {
  summary: string;
  keyPoints: string[];
  wordCount: number;
  needsEnrichment: boolean;
  wasEnriched?: boolean;
  sourceTruncated?: boolean;
  originalContentLength?: number;
  submittedContentLength?: number;
  compressionMethod?: 'pass-through' | 'extractive-summary' | 'truncate';
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
  private maxContextTokens?: number;
  private sessionLimitsLoaded: boolean;
  private readonly fallbackMaxContextTokens: number;
  private readonly promptTokenReserve: number;
  private readonly averageCharsPerToken: number;
  private readonly maxContentCharactersCap: number | null;

  constructor() {
    this.apiKey = env.CORTENSOR_API_KEY;

    this.apiUrl = `${env.CORTENSOR_BASE_URL}/api/v1/completions`;
    debugLog('🔗 Cortensor API URL:', this.apiUrl);

    this.sessionId = env.CORTENSOR_SESSION;
    this.promptType = env.CORTENSOR_PROMPT_TYPE;
    this.timeout = env.CORTENSOR_TIMEOUT;
    this.precommitTimeout = env.CORTENSOR_PRECOMMIT_TIMEOUT;
    this.maxTokens = env.CORTENSOR_MAX_TOKENS;
    this.temperature = env.CORTENSOR_TEMPERATURE;
    this.topP = env.CORTENSOR_TOP_P;
    this.topK = env.CORTENSOR_TOP_K;
    this.presencePenalty = env.CORTENSOR_PRESENCE_PENALTY;
    this.frequencyPenalty = env.CORTENSOR_FREQUENCY_PENALTY;
    this.stream = env.CORTENSOR_STREAM;

    this.sessionLimitsLoaded = false;
    this.fallbackMaxContextTokens = env.CORTENSOR_FALLBACK_MAX_CONTEXT_TOKENS;
    this.promptTokenReserve = env.CORTENSOR_PROMPT_TOKEN_RESERVE;
    this.averageCharsPerToken = env.CORTENSOR_AVG_CHARS_PER_TOKEN;
    const configuredMaxChars = env.CORTENSOR_MAX_CONTENT_CHARS;
    this.maxContentCharactersCap = Number.isFinite(configuredMaxChars) && configuredMaxChars > 0 ? configuredMaxChars : null;
  }

  private buildCompletionRequestPayload(prompt: string, clientReference: string) {
    return {
      session_id: this.sessionId,
      prompt_type: this.promptType,
      prompt,
      stream: this.stream,
      timeout: this.timeout,
      precommit_timeout: this.precommitTimeout,
      max_tokens: this.maxTokens,
      temperature: this.temperature,
      top_p: this.topP,
      top_k: this.topK,
      presence_penalty: this.presencePenalty,
      frequency_penalty: this.frequencyPenalty,
      client_reference: clientReference
    };
  }

  private buildAxiosConfig() {
    const timeoutMs = Number.isFinite(this.timeout) && this.timeout > 0
      ? (this.timeout + Math.max(this.precommitTimeout, 0) + 60) * 1000
      : 360000;

    return {
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      timeout: timeoutMs
    };
  }

  async generateSummary(article: ArticleContent, clientReference?: string): Promise<SummaryResult> {
    try {
      await this.ensureSessionLimits();

      const truncation = this.truncateArticleContent(article.content);
      const promptArticle: ArticleContent = { ...article, content: truncation.text };
      const prompt = this.createSummaryPrompt(promptArticle, truncation.truncated);
      const effectiveClientReference = clientReference ?? this.generateFallbackClientReference('summary');
      const requestPayload = this.buildCompletionRequestPayload(prompt, effectiveClientReference);

      debugLog('🧩 Cortensor request params:', {
        session_id: this.sessionId,
        prompt_type: this.promptType,
        max_tokens: this.maxTokens,
        timeout: this.timeout,
        precommit_timeout: this.precommitTimeout,
        temperature: this.temperature,
        top_p: this.topP,
        top_k: this.topK,
        presence_penalty: this.presencePenalty,
        frequency_penalty: this.frequencyPenalty,
        stream: this.stream
      });
      
      const response = await axios.post(
        this.apiUrl,
        requestPayload,
        this.buildAxiosConfig()
      );

      const summaryText = response.data.choices?.[0]?.text || response.data.text || '';
      
      // Parse the response to extract summary and key points
      const result = this.parseSummaryResponse(summaryText);
      
      // Check if summary needs enrichment
      result.needsEnrichment = this.shouldEnrich(result);
      result.wasEnriched = false;
      result.sourceTruncated = truncation.truncated;
      result.originalContentLength = truncation.originalLength;
      result.submittedContentLength = truncation.submittedLength;
  result.compressionMethod = truncation.method;
      
      return result;
      
    } catch (error) {
      console.error('Cortensor API error:', error);
      throw new Error('Failed to generate summary with Cortensor');
    }
  }

  async enrichSummary(
    originalSummary: SummaryResult,
    additionalSources: EnrichmentSource[],
    clientReference?: string
  ): Promise<SummaryResult> {
    try {
      const prompt = this.createEnrichmentPrompt(originalSummary, additionalSources);
      const effectiveClientReference = clientReference ?? this.generateFallbackClientReference('enrich');
      const requestPayload = this.buildCompletionRequestPayload(prompt, effectiveClientReference);
      
      const response = await axios.post(
        this.apiUrl,
        requestPayload,
        this.buildAxiosConfig()
      );

      const enrichedText = response.data.choices?.[0]?.text || response.data.text || '';
      const result = this.parseSummaryResponse(enrichedText);
      result.needsEnrichment = false; // Already enriched
      result.wasEnriched = true;
      result.sourceTruncated = originalSummary.sourceTruncated;
      result.originalContentLength = originalSummary.originalContentLength;
      result.submittedContentLength = originalSummary.submittedContentLength;
  result.compressionMethod = originalSummary.compressionMethod;

      return result;
      
    } catch (error) {
      console.error('Summary enrichment error:', error);
      // Return original summary if enrichment fails
      return originalSummary;
    }
  }

  private generateFallbackClientReference(label: string): string {
    const timestampSegment = Date.now().toString(36);
    const randomSegment = Math.random().toString(36).slice(2, 8);
    return `user-summarizer-${label}-${timestampSegment}${randomSegment}`;
  }

  private createSummaryPrompt(article: ArticleContent, wasTruncated = false): string {
    const truncationNotice = wasTruncated
      ? '\n\nNOTE: Source content was truncated to fit the model\'s context window. Summarize using only the provided content.'
      : '';

    return `You are a professional research analyst. Analyze the following article and provide a clean, well-structured summary.

Title: ${article.title}
Source: ${article.url}
Content: ${article.content}${truncationNotice}

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

  private async ensureSessionLimits(): Promise<void> {
    if (this.sessionLimitsLoaded) {
      return;
    }

    this.sessionLimitsLoaded = true;

    try {
      const discoveredLimit = await this.fetchContextLimit();
      if (typeof discoveredLimit === 'number') {
        this.maxContextTokens = discoveredLimit;
        debugLog('Cortensor session max context (tokens):', discoveredLimit);
        return;
      }
      console.warn(
        `Cortensor session response did not include a max context value. Falling back to ${this.fallbackMaxContextTokens}-token defaults.`
      );
    } catch (error) {
      console.warn(
        `Unable to fetch Cortensor session limits via HTTP. Using fallback ${this.fallbackMaxContextTokens}-token configuration.`
      );
      if (error instanceof Error) {
        console.warn(error.message);
      }
    }
  }

  private async fetchContextLimit(): Promise<number | null> {
    const timeoutMs = Number.isFinite(this.timeout) ? this.timeout * 1000 : 300000;
    const endpoints: string[] = [];

    const baseUrl = this.apiUrl.endsWith('/') ? this.apiUrl.slice(0, -1) : this.apiUrl;
    endpoints.push(`${baseUrl}/${this.sessionId}`);

    const sessionsUrl = baseUrl.replace(/\/completions$/, '/sessions');
    if (sessionsUrl !== baseUrl) {
      endpoints.push(`${sessionsUrl}/${this.sessionId}`);
    }

    const routerUrl = baseUrl.replace(/\/completions$/, '/router');
    if (routerUrl !== baseUrl) {
      endpoints.push(routerUrl);
    }

    for (const url of endpoints) {
      try {
        const response = await axios.get(url, {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json'
          },
          timeout: timeoutMs,
          validateStatus: (status) => status >= 200 && status < 400
        });

        const limitFromResponse = this.extractMaxContextTokens(response.data, response.headers as Record<string, unknown>);
        if (typeof limitFromResponse === 'number') {
          return limitFromResponse;
        }
      } catch (error) {
        if (axios.isAxiosError(error)) {
          const status = error.response?.status;
          if (status && [401, 403].includes(status)) {
            throw new Error(`Authorization failed while fetching context limits (status ${status}).`);
          }
          if (status && [400, 404, 405, 500].includes(status)) {
            // Expected for unsupported endpoints; try next option silently
            continue;
          }
        }
        throw error;
      }
    }

    return null;
  }

  private extractMaxContextTokens(data: unknown, headers: Record<string, unknown>): number | null {
    type ContextSource = Record<string, unknown>;
    const sourceRecord: ContextSource = (data && typeof data === 'object') ? (data as ContextSource) : {};

    const candidatePaths: Array<(source: ContextSource) => unknown> = [
      (source) => source?.max_context_tokens,
      (source) => source?.max_context_length,
      (source) => source?.max_context,
      (source) => source?.context_window,
      (source) => (source.session as ContextSource | undefined)?.max_context_tokens,
      (source) => (source.router as ContextSource | undefined)?.max_context_tokens,
      () => headers['x-cortensor-max-context'],
      () => headers['x-max-context-tokens'],
      () => headers['x-context-window']
    ];

    for (const getValue of candidatePaths) {
      const value = getValue(sourceRecord);
      const parsed = this.parseNumeric(value);
      if (parsed !== null) {
        return parsed;
      }
    }

    return null;
  }

  private parseNumeric(value: unknown): number | null {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === 'string') {
      const parsed = Number.parseInt(value, 10);
      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }
    return null;
  }

  private getMaxContextTokens(): number {
    const limit = typeof this.maxContextTokens === 'number' && this.maxContextTokens > 0
      ? this.maxContextTokens
      : this.fallbackMaxContextTokens;
    return Math.max(limit, 2048);
  }

  private getMaxContentCharacters(): number {
    const tokenLimit = this.getMaxContextTokens();
    const availableTokens = Math.max(tokenLimit - this.promptTokenReserve, Math.floor(tokenLimit * 0.5));
    const approxChars = Math.floor(availableTokens * this.averageCharsPerToken);
    const minBudget = Math.max(approxChars, 3500);
    if (this.maxContentCharactersCap) {
      return Math.min(minBudget, this.maxContentCharactersCap);
    }
    return minBudget;
  }

  private truncateArticleContent(content: string): {
    text: string;
    truncated: boolean;
    originalLength: number;
    submittedLength: number;
    method: 'pass-through' | 'extractive-summary' | 'truncate';
  } {
    const originalLength = content.length;
    const maxChars = this.getMaxContentCharacters();

    if (originalLength <= maxChars) {
      return {
        text: content,
        truncated: false,
        originalLength,
        submittedLength: originalLength,
        method: 'pass-through'
      };
    }

  const summary = this.buildExtractiveSummary(content, maxChars);
    if (summary) {
  const annotatedSummary = `${summary}\n\n[Content compressed from ${originalLength} to ${summary.length} characters to comply with model context limits.]`;
      console.warn(`Article content compressed from ${originalLength} to ${summary.length} characters using extractive summary.`);
      return {
        text: annotatedSummary,
        truncated: true,
        originalLength,
        submittedLength: annotatedSummary.length,
        method: 'extractive-summary'
      };
    }

    const excerpt = this.buildLeadingExcerpt(content, maxChars);
  const annotatedExcerpt = `${excerpt}\n\n[Content truncated after ${excerpt.length} of ${originalLength} characters to comply with model context limits.]`;
    console.warn(`Article content truncated from ${originalLength} to ${excerpt.length} characters as a fallback to fit context window.`);

    return {
      text: annotatedExcerpt,
      truncated: true,
      originalLength,
      submittedLength: annotatedExcerpt.length,
      method: 'truncate'
    };
  }

  private buildExtractiveSummary(content: string, maxChars: number): string | null {
    const normalized = content.replace(/\s+/g, ' ').trim();
    if (normalized.length === 0) {
      return null;
    }

    const sentenceSplitRegex = /(?<=[.!?。！？])\s+(?=[A-Z0-9])/g;
    const sentences = normalized.split(sentenceSplitRegex).map(sentence => sentence.trim()).filter(Boolean);

    if (sentences.length < 4) {
      return null;
    }

    const stopWords = new Set([
      'the','is','in','at','of','a','an','and','to','for','with','on','by','from','as','that','this','it','be','are','was','were','or','but','if','then','so','than','too','very','into','about','over','after','before','between','through','during','while','because','what','which','who','whom','whose','can','could','should','would'
    ]);

    const frequencies = new Map<string, number>();

    const sentenceTokens = sentences.map(sentence => {
      const tokens = sentence.toLowerCase().match(/[a-z0-9']+/g) || [];
      return tokens.filter(token => !stopWords.has(token));
    });

    for (const tokens of sentenceTokens) {
      for (const token of tokens) {
        frequencies.set(token, (frequencies.get(token) || 0) + 1);
      }
    }

    if (frequencies.size === 0) {
      return null;
    }

    const scoredSentences = sentences.map((sentence, index) => {
      const tokens = sentenceTokens[index];
      const score = tokens.reduce((acc, token) => acc + (frequencies.get(token) || 0), 0);
      const normalizedScore = tokens.length > 0 ? score / tokens.length : 0;
      return { sentence, index, score: normalizedScore };
    });

    const sortedByScore = scoredSentences
      .filter(item => item.sentence.length > 40)
      .sort((a, b) => b.score - a.score);

    if (sortedByScore.length === 0) {
      return null;
    }

    const selected: typeof sortedByScore = [];
    let currentLength = 0;
  const targetLength = Math.max(Math.floor(maxChars * 0.75), maxChars - 2000);

    for (const candidate of sortedByScore) {
      const newLength = currentLength === 0
        ? candidate.sentence.length
        : currentLength + 1 + candidate.sentence.length;

      if (newLength > targetLength) {
        continue;
      }

      selected.push(candidate);
      currentLength = newLength;

      if (currentLength >= targetLength) {
        break;
      }
    }

    if (selected.length < 3) {
      return null;
    }

    const ordered = selected.sort((a, b) => a.index - b.index).map(item => item.sentence);
    const summary = ordered.join(' ');
    return summary.length <= maxChars ? summary : summary.slice(0, maxChars);
  }

  private buildLeadingExcerpt(content: string, maxChars: number): string {
    const sentences = content.split(/(?<=[.!?。！？])\s+/);
    let collected = '';

    for (const sentence of sentences) {
      if (!sentence) continue;
      const trimmedSentence = sentence.trim();
      if (!trimmedSentence) continue;
      const nextLength = collected.length === 0 ? trimmedSentence.length : collected.length + 1 + trimmedSentence.length;
      if (nextLength > maxChars) {
        break;
      }
      collected = collected.length === 0 ? trimmedSentence : `${collected} ${trimmedSentence}`;
    }

    if (collected.length < Math.ceil(maxChars * 0.5)) {
      collected = content.slice(0, maxChars);
      const lastSentenceBoundary = Math.max(
        collected.lastIndexOf('. '),
        collected.lastIndexOf('! '),
        collected.lastIndexOf('? '),
        collected.lastIndexOf('\n\n')
      );
      if (lastSentenceBoundary > maxChars * 0.2) {
        collected = collected.slice(0, lastSentenceBoundary + 1);
      }
    }

    return collected.trim();
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
    const minParagraphs = env.MIN_SUMMARY_PARAGRAPHS;
    const paragraphCount = summary.summary.split('\n\n').length;
    
    return (
      summary.wordCount < 200 || 
      paragraphCount < minParagraphs ||
      summary.keyPoints.length < 4
    );
  }
}