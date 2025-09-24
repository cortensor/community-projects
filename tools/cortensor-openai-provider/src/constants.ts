/**
 * Default configuration constants for Cortensor Provider
 * 
 * This file centralizes all default values used throughout the provider
 * to ensure consistency and easy maintenance.
 */

/**
 * Default model configuration values
 */
export const DEFAULT_MODEL_CONFIG = {
  modelName: 'cortensor-chat',
  temperature: 0.5,
  maxTokens: 64000,
  topP: 0.95,
  topK: 40,
  presencePenalty: 0,
  frequencyPenalty: 0,
  stream: false,
  timeout: 60 * 15,
  promptType: 1,
  promptTemplate: ''
} as const;
export const MAX_INPUT_TOKEN = 20000;

/**
 * Maximum number of words to include from search result snippets
 * This helps keep the context focused and prevents overwhelming the AI with too much information
 */
export const SEARCH_SNIPPET_WORD_LIMIT = 200;

