/**
 * Cortensor API Transformers
 * 
 * This module handles the conversion between OpenAI format and Cortensor API format.
 * It provides utilities to transform requests and responses between the two formats,
 * enabling seamless integration with the Vercel AI SDK.
 */

import type { CoreMessage } from 'ai';
import type {
  CortensorModelConfig,
  WebSearchResult,
  WebSearchCallback,
  CortensorRequest,
  CortensorResponse,
  CortensorChoice,
  CortensorUsage,
  OpenAIRequest,
  OpenAIResponse,
  SearchDirectives,
  CortensorTransformResult
} from './types';
import { WebSearchError, ConfigurationError } from './provider';
import { DEFAULT_MODEL_CONFIG, MAX_INPUT_TOKEN } from './constants';
import { extractSearchDirectives, generateSearchQuery, buildPromptWithSearchResults } from './websearch';
import { buildFormattedPrompt, createErrorResponse, formatSearchResults } from './utils';
import { handleWebSearch } from './websearch';










/**
 * Sanitizes message content by removing unwanted tokens and patterns
 * @param content - The content to sanitize
 * @returns Sanitized content
 */
function sanitizeMessageContent(content: string): string {
  let sanitized = content
    .replace(/<\/s>/g, '')  // Remove </s> stop tokens
    .replace(/<s>/g, '')    // Remove <s> start tokens
    .replace(/\[INST\]/g, '') // Remove instruction tokens
    .replace(/\[\/INST\]/g, '') // Remove end instruction tokens
    .trim();
    
  return sanitized;
}

/**
 * Transforms OpenAI request format to Cortensor API format
 * @param requestBody - The OpenAI-formatted request body as string
 * @param sessionId - The session ID to include in the request
 * @param modelConfig - Optional model configuration to override defaults
 * @returns Cortensor transform result with request and optional web search data
 */
export async function transformToCortensor(
  requestBody: string,
  sessionId: number,
  modelConfig?: CortensorModelConfig
): Promise<CortensorTransformResult> {

  try {
    const openAIRequest: OpenAIRequest = JSON.parse(requestBody);


    // Extract search directives and clean messages
    const searchDirectives = extractSearchDirectives(openAIRequest.messages, modelConfig?.webSearch);

    let finalPrompt: string = '';
    let webSearchResults: WebSearchResult[] | undefined;
    let searchQuery: string | undefined;

    // Handle web search if needed
    if (searchDirectives.shouldSearch && modelConfig?.webSearch?.provider) {

      try {
        // Perform web search using flexible provider
        const searchResult = await handleWebSearch(
          searchDirectives.cleanedMessages,
          modelConfig.webSearch
        );
        
        if (searchResult) {
          webSearchResults = searchResult.results || [];
          searchQuery = searchResult.query;

          // Build enhanced prompt with search results
          finalPrompt = buildPromptWithSearchResults(
            searchDirectives.cleanedMessages,
            webSearchResults || [],
            searchQuery
          );
        }

      } catch (error) {
        if (error instanceof ConfigurationError) {
          throw error;
        }
        // Fall through to standard prompt building
      }
    }

    // Build standard prompt if no search or search failed
    if (!finalPrompt) {
      const systemMessages = searchDirectives.cleanedMessages.filter(msg => msg.role === 'system');
      const conversationMessages = searchDirectives.cleanedMessages.filter(msg => msg.role !== 'system');

      finalPrompt = buildFormattedPrompt(systemMessages, conversationMessages);
    }

    // Sanitize the final prompt before sending to AI
    const sanitizedPrompt = sanitizeMessageContent(finalPrompt);

    // Create Cortensor request with model config or defaults
    const cortensorRequest: CortensorRequest = {
      session_id: sessionId,
      prompt: sanitizedPrompt,
      prompt_type: modelConfig?.promptType ?? DEFAULT_MODEL_CONFIG.promptType,
      prompt_template: modelConfig?.promptTemplate ?? DEFAULT_MODEL_CONFIG.promptTemplate,
      stream: modelConfig?.stream ?? DEFAULT_MODEL_CONFIG.stream,
      timeout: modelConfig?.timeout ?? DEFAULT_MODEL_CONFIG.timeout,
      client_reference: `user-request-${Date.now()}`,
      max_tokens: modelConfig?.maxTokens ?? DEFAULT_MODEL_CONFIG.maxTokens,
      temperature: modelConfig?.temperature ?? openAIRequest.temperature ?? DEFAULT_MODEL_CONFIG.temperature,
      top_p: modelConfig?.topP ?? DEFAULT_MODEL_CONFIG.topP,
      top_k: modelConfig?.topK ?? DEFAULT_MODEL_CONFIG.topK,
      presence_penalty: modelConfig?.presencePenalty ?? DEFAULT_MODEL_CONFIG.presencePenalty,
      frequency_penalty: modelConfig?.frequencyPenalty ?? DEFAULT_MODEL_CONFIG.frequencyPenalty
    };



    const result: CortensorTransformResult = {
      request: cortensorRequest
    };

    if (webSearchResults) {
      result.webSearchResults = webSearchResults;
    }

    if (searchQuery) {
      result.searchQuery = searchQuery;
    }

    return result;
  } catch (error) {
    throw new Error('Failed to transform request to Cortensor format');
  }
}



/**
 * Transforms Cortensor response to OpenAI format
 * @param cortensorResponse - The response from Cortensor API
 * @param webSearchResults - Optional web search results to include as tool calls
 * @param searchQuery - The search query used (if any)
 * @returns Promise<Response> - OpenAI-formatted response
 */
export async function transformToOpenAI(
  cortensorResponse: Response,
  webSearchResults?: WebSearchResult[],
  searchQuery?: string
): Promise<Response> {

  try {
    const cortensorData = await cortensorResponse.json() as CortensorResponse;

    // Transform choices to OpenAI format
    const transformedChoices = cortensorData.choices.map((choice: CortensorChoice, index: number) => {
      let content = choice.text || '';
      content = sanitizeMessageContent(content);

      // Validate that we have substantial content from the AI
      const hasSubstantialContent = content.trim().length > 50; // At least 50 characters of meaningful content
      
      // If content is too brief and we have search results, add a note about the issue
      if (!hasSubstantialContent && webSearchResults && webSearchResults.length > 0) {
        content = content || 'Based on the search results provided:';
      }

      // Append search results as markdown URLs to content if they exist
      if (webSearchResults && webSearchResults.length > 0) {
        const searchResultsMarkdown = formatSearchResults(webSearchResults);
        if (searchResultsMarkdown) {
          // Only add "Search Results" header if the AI's response doesn't already reference them
          const needsHeader = !content.toLowerCase().includes('search result') && !content.toLowerCase().includes('source');
          const separator = needsHeader ? `\n\n**Sources Referenced:** ${searchResultsMarkdown}` : `\n\n${searchResultsMarkdown}`;
          content += separator;
        }
      }

      const message: any = {
        role: 'assistant' as const,
        content: content
      };

      const transformedChoice = {
        index: choice.index ?? index,
        message,
        finish_reason: choice.finish_reason || 'stop'
      };

      return transformedChoice;
    });

    // Transform usage information
    const transformedUsage = cortensorData.usage ? {
      prompt_tokens: cortensorData.usage.prompt_tokens,
      completion_tokens: cortensorData.usage.completion_tokens,
      total_tokens: cortensorData.usage.total_tokens
    } : {
      prompt_tokens: 0,
      completion_tokens: 0,
      total_tokens: 0
    };

    // Create OpenAI-formatted response
    const openAIResponse: OpenAIResponse = {
      id: cortensorData.id || `cortensor-${Date.now()}`,
      object: 'chat.completion',
      created: cortensorData.created || Math.floor(Date.now() / 1000),
      model: cortensorData.model || 'cortensor-model',
      choices: transformedChoices,
      usage: transformedUsage
    };

    // Return as Response object
    const responseBody = JSON.stringify(openAIResponse);
    
    const finalResponse = new Response(
      responseBody,
      {
        status: cortensorResponse.status,
        statusText: cortensorResponse.statusText,
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );

    return finalResponse;
  } catch (error) {
    // Return standardized error response
    const errorResponse = createErrorResponse();

    const errorResponseBody = JSON.stringify(errorResponse);
    
    return new Response(
      errorResponseBody,
      {
        status: 500,
        statusText: 'Internal Server Error',
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

// ============================================================================
// NOTES
// ============================================================================
// - Streaming is currently disabled - all responses are sent at once
// - The transformer handles both successful responses and error cases
// - All responses are converted to OpenAI-compatible format for SDK integration