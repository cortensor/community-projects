/**
 * Cortensor AI Provider
 * 
 * A drop-in OpenAI-compatible provider for the Cortensor API that works seamlessly
 * with the Vercel AI SDK and any framework that supports OpenAI providers.
 * 
 * @example
 * ```typescript
 * import { cortensorProvider, cortensorModel } from 'cortensor-ai-provider';
 * import { generateText } from 'ai';
 * 
 * // Using the provider directly
 * const result = await generateText({
 *   model: cortensorProvider('cortensor-chat'),
 *   prompt: 'Hello, world!',
 * });
 * 
 * // Using the model with configuration
 * const model = cortensorModel({
 *   sessionId: 123,
 *   temperature: 0.7,
 *   maxTokens: 1000,
 * });
 * 
 * const result = await generateText({
 *   model,
 *   prompt: 'Tell me a story',
 * });
 * ```
 */



// Main provider exports
export {
  cortensorProvider,
  cortensorModel,
  createCortensorProvider,
  extractModelConfiguration,
} from './provider';

// Constants exports
export {
  DEFAULT_MODEL_CONFIG,
} from './constants';


// All other type exports from types
export type * from './types';

// Tavily provider exports
export {
  createTavilySearch,
} from './providers/tavily';


// Transformer function exports
export {
  transformToCortensor,
  transformToOpenAI,
} from './transformers';

// Web search function exports
export {
  extractSearchDirectives,
  generateSearchQuery,
  buildPromptWithSearchResults,
} from './websearch';

// Utility function exports
export {
  formatSearchResults,
} from './utils';