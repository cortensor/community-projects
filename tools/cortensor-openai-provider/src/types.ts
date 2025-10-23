/**
 * TypeScript Type Definitions for Cortensor OpenAI Provider
 * 
 * This module contains all the interface and type definitions used throughout
 * the Cortensor OpenAI Provider package for type safety and consistency.
 */

import type { CoreMessage } from 'ai';


// ============================================================================
// RE-EXPORTED TYPES FROM PROVIDER
// ============================================================================


/**
 * Simple options for Tavily search
 */
export interface TavilySearchOptions {
  maxResults?: number;
  apiKey?: string;
  includeImages?: boolean;
  searchDepth?: 'basic' | 'advanced';
}

// ============================================================================
// CORTENSOR API TYPES
// ============================================================================

/**
 * Request format expected by the Cortensor API
 */
export interface CortensorRequest {
  session_id: number;
  prompt: string;
  prompt_type?: number;
  prompt_template?: string;
  stream?: boolean;
  timeout?: number;
  client_reference?: string;
  max_tokens?: number;
  temperature?: number;
  top_p?: number;
  top_k?: number;
  presence_penalty?: number;
  frequency_penalty?: number;
}

/**
 * Individual choice in Cortensor API response
 */
export interface CortensorChoice {
  finish_reason: string;
  index: number;
  logprobs: null | any;
  text: string;
}

/**
 * Token usage information from Cortensor API
 */
export interface CortensorUsage {
  completion_tokens: number;
  prompt_tokens: number;
  total_tokens: number;
}

/**
 * Response format from Cortensor API
 */
export interface CortensorResponse {
  choices: CortensorChoice[];
  created: number;
  id: string;
  model: string;
  object: string;
  usage: CortensorUsage;
}

// ============================================================================
// OPENAI API TYPES
// ============================================================================

/**
 * Request format from OpenAI/Vercel AI SDK
 */
export interface OpenAIRequest {
  model: string;
  messages: CoreMessage[];
  stream?: boolean;
  temperature?: number;
  max_tokens?: number;
  [key: string]: unknown;
}

/**
 * Message structure in OpenAI response
 */
export interface OpenAIMessage {
  role: string;
  content: string | null;
  refusal?: string | null;
}

/**
 * Choice structure in OpenAI response
 */
export interface OpenAIChoice {
  index: number;
  message: OpenAIMessage;
  finish_reason: string | null;
  logprobs?: any | null;
}

/**
 * Usage information in OpenAI response
 */
export interface OpenAIUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

/**
 * Response format expected by OpenAI/Vercel AI SDk
 */
export interface OpenAIResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: OpenAIChoice[];
  usage?: OpenAIUsage;
  system_fingerprint?: string;
}

// ============================================================================
// WEB SEARCH TYPES
// ============================================================================

/**
 * Search directive information extracted from messages
 */
export interface SearchDirectives {
  shouldSearch: boolean;
  cleanedMessages: CoreMessage[];
}

/**
 * Result of transforming to Cortensor format with optional web search data
 */
export interface CortensorTransformResult {
  request: CortensorRequest;
  webSearchResults?: WebSearchResult[];
  searchQuery?: string;
}


// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

/**
 * Configuration options for Cortensor provider
 */
export interface CortensorConfig {
  /** API key for authentication (optional, defaults to env var) */
  apiKey?: string;
  /** Base URL for the API (optional, defaults to env var) */
  baseURL?: string;
  /** Request timeout in seconds */
  timeout?: number;
  /** Session timeout in seconds */
  sessionTimeout?: number;
}

/**
 * Web search result structure
 */
export interface WebSearchResult {
  title: string;
  url: string;
  snippet: string;
  publishedDate?: string;
}

/**
 * Web search request structure
 */
export interface WebSearchRequest {
  query: string;
  maxResults: number;
}

/**
 * Web search configuration options
 */
export interface WebSearchConfig {
  mode: 'prompt' | 'force' | 'disable';
  provider?: WebSearchCallback;
  maxResults?: number;
}

/**
 * Model configuration options for Cortensor models
 */
export interface CortensorModelConfig {
  /** Required session ID for the conversation */
  sessionId: number;
  /** Model name identifier */
  modelName?: string;
  /** Sampling temperature (0.0 to 2.0) */
  temperature?: number;
  /** Maximum tokens to generate */
  maxTokens?: number;
  /** Top-p sampling parameter */
  topP?: number;
  /** Top-k sampling parameter */
  topK?: number;
  /** Presence penalty (-2.0 to 2.0) */
  presencePenalty?: number;
  /** Frequency penalty (-2.0 to 2.0) */
  frequencyPenalty?: number;
  /** Whether to stream responses */
  stream?: boolean;
  /** Request timeout in seconds */
  timeout?: number;
  /** Prompt type identifier */
  promptType?: number;
  /** Custom prompt template */
  promptTemplate?: string;
  /** Web search configuration */
  webSearch?: WebSearchConfig;
}


// ============================================================================
// WEB SEARCH INTERFACES
// ============================================================================

/**
 * Base interface for web search providers
 */
export interface WebSearchProvider {
  search(query: string, maxResults?: number): Promise<WebSearchResult[]>;
}

/**
 * Flexible callback type - can be a provider or direct function
 */
export type WebSearchCallback =
  | WebSearchProvider
  | ((query: string, maxResults?: number) => Promise<WebSearchResult[]>);

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================
