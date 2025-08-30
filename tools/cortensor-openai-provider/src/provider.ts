/**
 * Cortensor Provider for Mastra AI
 * 
 * This module provides integration between the Cortensor API and the Vercel AI SDK.
 * It creates an OpenAI-compatible interface that handles session management,
 * request/response transformations, and error handling automatically.
 */

import { createOpenAICompatible } from '@ai-sdk/openai-compatible';
import { transformToCortensor, transformToOpenAI } from './transformers';
import type { CortensorConfig, CortensorModelConfig, WebSearchResult, WebSearchCallback } from './types';
import { DEFAULT_MODEL_CONFIG } from './constants';

// Global registry for web search providers to handle function serialization
const webSearchProviderRegistry = new Map<string, WebSearchCallback>();
let providerIdCounter = 0;

// ============================================================================
// ENVIRONMENT CONFIGURATION
// ============================================================================

// Load environment variables (validation happens at runtime)
const CORTENSOR_API_KEY = process.env.CORTENSOR_API_KEY;
const CORTENSOR_BASE_URL = process.env.CORTENSOR_BASE_URL;

// ============================================================================
// CUSTOM ERROR CLASSES
// ============================================================================

/**
 * Base error class for Cortensor-related errors
 */
export class CortensorError extends Error {
  constructor(message: string, public code: string) {
    super(message);
    this.name = 'CortensorError';
  }
}

/**
 * Error thrown when web search operations fail
 */
export class WebSearchError extends CortensorError {
  constructor(message: string) {
    super(message, 'WEB_SEARCH_ERROR');
  }
}

/**
 * Error thrown when configuration is invalid
 */
export class ConfigurationError extends CortensorError {
  constructor(message: string) {
    super(message, 'CONFIGURATION_ERROR');
  }
}

/**
 * Validates Cortensor configuration at runtime
 * @param apiKey - API key to validate
 * @param baseUrl - Base URL to validate
 * @throws ConfigurationError if validation fails
 */
function validateCortensorConfig(apiKey?: string, baseUrl?: string): void {
  if (!apiKey) {
    throw new ConfigurationError(
      'CORTENSOR_API_KEY is required. Set it as environment variable or pass it explicitly.'
    );
  }
  if (!baseUrl) {
    throw new ConfigurationError(
      'CORTENSOR_BASE_URL is required. Set it as environment variable or pass it explicitly.'
    );
  }
}


/**
 * Extracts model configuration and session ID from request body
 * @param requestBody - The request body as string
 * @returns Object containing sessionId and modelConfig with defaults applied
 * @throws Error if configuration cannot be extracted
 */
export function extractModelConfiguration(requestBody: string): {
  sessionId: number;
  modelConfig?: CortensorModelConfig;
} {
  try {
    const parsedBody = JSON.parse(requestBody);

    const modelName = parsedBody.model;

    if (typeof modelName !== 'string') {
      throw new Error('Model name must be a string');
    }



    // Extract configuration from model name (format: modelname-config-base64encodedconfig)
    const configMatch = modelName.match(/-config-([A-Za-z0-9+/=]+)$/);
    if (!configMatch || !configMatch[1]) {
      throw new Error('Configuration not found in model name. Model name should end with "-config-{base64EncodedConfig}"');
    }



    // Decode the base64 encoded configuration
    const configBase64 = configMatch[1];
    const configJson = Buffer.from(configBase64, 'base64').toString('utf-8');
    const decodedConfig = JSON.parse(configJson) as Partial<CortensorModelConfig>;


    if (!decodedConfig.sessionId) {
      throw new Error('Session ID not found in model configuration');
    }



    // Merge decoded configuration with defaults

    const modelConfig: CortensorModelConfig = {
      sessionId: decodedConfig.sessionId,
      modelName: decodedConfig.modelName ?? DEFAULT_MODEL_CONFIG.modelName,
      temperature: decodedConfig.temperature ?? DEFAULT_MODEL_CONFIG.temperature,
      maxTokens: decodedConfig.maxTokens ?? DEFAULT_MODEL_CONFIG.maxTokens,
      topP: decodedConfig.topP ?? DEFAULT_MODEL_CONFIG.topP,
      topK: decodedConfig.topK ?? DEFAULT_MODEL_CONFIG.topK,
      presencePenalty: decodedConfig.presencePenalty ?? DEFAULT_MODEL_CONFIG.presencePenalty,
      frequencyPenalty: decodedConfig.frequencyPenalty ?? DEFAULT_MODEL_CONFIG.frequencyPenalty,
      stream: decodedConfig.stream ?? DEFAULT_MODEL_CONFIG.stream,
      timeout: decodedConfig.timeout ?? DEFAULT_MODEL_CONFIG.timeout,
      promptType: decodedConfig.promptType ?? DEFAULT_MODEL_CONFIG.promptType,
      promptTemplate: decodedConfig.promptTemplate ?? DEFAULT_MODEL_CONFIG.promptTemplate
    };

    // Copy web search configuration if present
    if (decodedConfig.webSearch) {
      modelConfig.webSearch = { ...decodedConfig.webSearch };

      // Restore web search provider function from registry if it's a reference
      if (modelConfig.webSearch.provider && typeof modelConfig.webSearch.provider === 'string' && (modelConfig.webSearch.provider as string).startsWith('provider_')) {
        const providerId = modelConfig.webSearch.provider as string;
        const providerFunction = webSearchProviderRegistry.get(providerId);

        if (providerFunction) {
          modelConfig.webSearch.provider = providerFunction;
        } else {
          delete modelConfig.webSearch.provider;
        }
      }
    }



    const result = {
      sessionId: modelConfig.sessionId,
      modelConfig
    };

    return result;
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    throw new Error(`Failed to extract model configuration: ${errorMessage}`);
  }
}

/**
 * Creates a standardized error response for the provider
 * @param error - The error that occurred
 * @returns Response object with error details
 */
function createProviderErrorResponse(error: unknown): Response {
  let errorMessage = 'Unknown error';
  let errorCode = 'UNKNOWN_ERROR';
  let statusCode = 500;

  if (error instanceof CortensorError) {
    errorMessage = error.message;
    errorCode = error.code;

    // Set appropriate status codes for different error types
    if (error instanceof ConfigurationError) {
      statusCode = 400; // Bad Request
    } else if (error instanceof WebSearchError) {
      statusCode = 502; // Bad Gateway
    }
  } else if (error instanceof Error) {
    errorMessage = error.message;
  }

  const errorResponse = {
    error: {
      message: errorMessage,
      type: 'provider_error',
      code: errorCode
    }
  };

  return new Response(
    JSON.stringify(errorResponse),
    {
      status: statusCode,
      headers: {
        'Content-Type': 'application/json'
      }
    }
  );
}

/**
 * Handles the core request processing logic
 * @param requestBody - The request body as string
 * @returns Promise<Response> - The processed response
 */
async function processRequest(requestBody: string): Promise<Response> {
  // Extract configuration from request
  const { sessionId, modelConfig } = extractModelConfiguration(requestBody);

  // Transform to Cortensor format
  const transformResult = await transformToCortensor(requestBody, sessionId, modelConfig);

  // Prepare API request
  const cortensorUrl = `${CORTENSOR_BASE_URL}/api/v1/completions`;

  const cortensorOptions: RequestInit = {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${CORTENSOR_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(transformResult.request),
  };

  // Make API call
  const cortensorResponse = await fetch(cortensorUrl, cortensorOptions);

  if (!cortensorResponse.ok) {
    throw new Error(`Cortensor API error: ${cortensorResponse.status} ${cortensorResponse.statusText}`);
  }

  // Process response
  const responseText = await cortensorResponse.text();

  const cortensorResponseClone = new Response(responseText, {
    status: cortensorResponse.status,
    statusText: cortensorResponse.statusText,
    headers: cortensorResponse.headers
  });

  // Transform back to OpenAI format with web search results
  const finalResponse = await transformToOpenAI(cortensorResponseClone, transformResult.webSearchResults, transformResult.searchQuery);

  return finalResponse;
}

// ============================================================================
// MAIN PROVIDER
// ============================================================================

/**
 * Main Cortensor provider using OpenAI-compatible interface
 * Handles session management and format transformations automatically
 */
export const cortensorProvider = createOpenAICompatible({
  name: 'cortensor',
  baseURL: `${CORTENSOR_BASE_URL}`,
  headers: {
    'Authorization': `Bearer ${CORTENSOR_API_KEY || ''}`,
    'Content-Type': 'application/json',
  },
  fetch: async (input, options: RequestInit = {}) => {
    try {
      // Validate configuration at runtime
      validateCortensorConfig(CORTENSOR_API_KEY, CORTENSOR_BASE_URL);

      const requestBody = options.body as string;

      const result = await processRequest(requestBody);

      return result;
    } catch (error) {
      const errorResponse = createProviderErrorResponse(error);

      return errorResponse;
    }
  },
});

// ============================================================================
// MODEL CREATION UTILITIES
// ============================================================================

/**
 * Creates a configurable Cortensor model with custom parameters
 * @param config - Configuration options for the model (optional, uses defaults if not provided)
 * @returns Cortensor model instance with applied configuration
 */
export function cortensorModel(config: { sessionId: number } & Partial<Omit<CortensorModelConfig, 'sessionId'>>): ReturnType<typeof cortensorProvider> {
  // Validate required session ID
  if (!config.sessionId) {
    throw new Error('Session ID is required for Cortensor model creation');
  }

  // Only include explicitly provided configuration values
  const configToEncode: Partial<CortensorModelConfig> = {
    sessionId: config.sessionId
  };

  // Add only the properties that were explicitly provided
  if (config.modelName !== undefined) configToEncode.modelName = config.modelName;
  if (config.temperature !== undefined) configToEncode.temperature = config.temperature;
  if (config.maxTokens !== undefined) configToEncode.maxTokens = config.maxTokens;
  if (config.topP !== undefined) configToEncode.topP = config.topP;
  if (config.topK !== undefined) configToEncode.topK = config.topK;
  if (config.presencePenalty !== undefined) configToEncode.presencePenalty = config.presencePenalty;
  if (config.frequencyPenalty !== undefined) configToEncode.frequencyPenalty = config.frequencyPenalty;
  if (config.stream !== undefined) configToEncode.stream = config.stream;
  if (config.timeout !== undefined) configToEncode.timeout = config.timeout;
  if (config.promptType !== undefined) configToEncode.promptType = config.promptType;
  if (config.promptTemplate !== undefined) configToEncode.promptTemplate = config.promptTemplate;

  // Handle web search configuration with provider function serialization
  if (config.webSearch !== undefined) {
    const webSearchConfig = { ...config.webSearch };

    // If there's a provider function, store it in the registry and use a reference
    if (webSearchConfig.provider && typeof webSearchConfig.provider === 'function') {
      const providerId = `provider_${providerIdCounter++}_${Date.now()}`;
      webSearchProviderRegistry.set(providerId, webSearchConfig.provider);

      // Replace the function with a reference
      configToEncode.webSearch = {
        ...webSearchConfig,
        provider: providerId as any // Store the ID instead of the function
      };
    } else {
      configToEncode.webSearch = webSearchConfig;
    }
  }

  // Encode configuration as base64 JSON and embed in model name
  const configJson = JSON.stringify(configToEncode);
  const configBase64 = Buffer.from(configJson, 'utf-8').toString('base64');
  const modelName = config.modelName || DEFAULT_MODEL_CONFIG.modelName;
  const uniqueModelName = `${modelName}-config-${configBase64}`;
  
  // Create model instance with unique name that contains encoded configuration
  const modelInstance = cortensorProvider(uniqueModelName);

  return modelInstance;
}


// ============================================================================
// EXPORTS
// ============================================================================

// Re-export transformer functions for convenience
export { transformToCortensor, transformToOpenAI } from './transformers';



// ============================================================================
// CUSTOM PROVIDER FACTORY
// ============================================================================

// Note: Model configurations are now embedded directly in model names as base64 JSON,
// so no global state management or cleanup functions are needed.

/**
 * Creates a custom Cortensor provider with specific configuration
 * @param config - Configuration options to override defaults
 * @returns Configured Cortensor provider instance
 */
export function createCortensorProvider(config: CortensorConfig = {}) {
  // Use provided config or fall back to environment variables
  const apiKey = config.apiKey || CORTENSOR_API_KEY;
  const baseURL = config.baseURL || `${CORTENSOR_BASE_URL}/v1`;

  // Validate configuration
  if (!apiKey) {
    throw new Error('API key is required for custom Cortensor provider');
  }

  /**
   * Custom request processor for the provider
   * @param requestBody - The request body as string
   * @returns Promise<Response> - The processed response
   */
  async function processCustomRequest(requestBody: string): Promise<Response> {
    // Extract configuration from request
    const { sessionId, modelConfig } = extractModelConfiguration(requestBody);

    // Transform to Cortensor format
    const cortensorRequest = transformToCortensor(requestBody, sessionId, modelConfig);

    // Prepare API request with custom config
    const cortensorUrl = `${CORTENSOR_BASE_URL}/api/v1/completions`;
    
    const cortensorOptions: RequestInit = {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(cortensorRequest),
    };

    // Make API call
    const cortensorResponse = await fetch(cortensorUrl, cortensorOptions);

    if (!cortensorResponse.ok) {
      throw new Error(`Cortensor API error: ${cortensorResponse.status} ${cortensorResponse.statusText}`);
    }

    // Process response
    const responseText = await cortensorResponse.text();

    const cortensorResponseClone = new Response(responseText, {
      status: cortensorResponse.status,
      statusText: cortensorResponse.statusText,
      headers: cortensorResponse.headers
    });

    // Transform back to OpenAI format
    const result = await transformToOpenAI(cortensorResponseClone);
    
    return result;
  }

  // Return configured provider
  return createOpenAICompatible({
    name: 'cortensor-custom',
    baseURL,
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    fetch: async (input, options: RequestInit = {}) => {
      try {
        const requestBody = options.body as string;
        
        const result = await processCustomRequest(requestBody);
        
        return result;
      } catch (error) {
        return createProviderErrorResponse(error);
      }
    }
  });
}
