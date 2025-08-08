// src/app/api/chat/route.ts
// Enhanced Eureka API with dual streaming architecture:
// - Default Model (Llava 1.5): Uses clean processing for professional responses
// - Deepseek Model: Uses DeepSeek R1 advanced features for enhanced reasoning and formatting
import { headers } from 'next/headers'
import { appConfig } from '../../../lib/app-config';
import { apiLogger } from '../../../lib/logger';
import { NextRequest, NextResponse } from 'next/server';

// Model-specific filtering configurations
const modelFilters = {
  'default-model': {
    name: 'Default Model',
    removeThinkingBlocks: true, // Always remove thinking blocks for clean output
    removeVerbosePatterns: true,
    cleanupPatterns: [
      /<thinking>[\s\S]*?<\/thinking>/gi,
      /<\/?thinking>/gi,
      /Final Response:|final response:/gi,
      /<\|USER\|>[\s\S]*?<\|ASSISTANT\|>/gi,
      /USER[\s\S]*?ASSISTANT/gi,
    ],
    preserveCodeBlocks: true
  },
  'deepseek-r1': {
    name: 'Deepseek R1', 
    removeThinkingBlocks: true, // Remove thinking blocks
    removeVerbosePatterns: false,
    cleanupPatterns: [
      /<thinking>[\s\S]*?<\/thinking>/gi,
      /<\/?thinking>/gi,
      /^<\/?thinking>?$/gi,
      /<\/think>/gi, // Remove stray </think> tags
      /<think>/gi,   // Remove stray <think> tags
      /\s*<\/think>\s*/gi, // Remove </think> with surrounding whitespace
    ],
    preserveCodeBlocks: true
  }
};

// Enhanced text filtering function with thinking process control
function applyModelFilters(text: string, modelId: string, isDeepThinking: boolean = false, showThinkingProcess: boolean = false): string {
  const modelConfig = modelFilters[modelId as keyof typeof modelFilters] || modelFilters['default-model'];
  
  let filteredText = text;
  
  // For DeepSeek R1 - extract thinking process from start to </think>
  if (modelId === 'deepseek-r1') {
    const thinkEndIndex = filteredText.indexOf('</think>');
    
    if (thinkEndIndex !== -1) {
      // Extract thinking process (from start to </think>)
      const thinkingContent = filteredText.substring(0, thinkEndIndex).trim();
      // Extract main response (after </think>)
      const mainResponse = filteredText.substring(thinkEndIndex + 8).trim(); // 8 = length of '</think>'
      
      if (showThinkingProcess && thinkingContent && thinkingContent.length > 0) {
        // Show thinking process as built-in feature for DeepSeek
        return `🧠 **Thinking Process:**\n\n${thinkingContent}\n\n---\n\n**Response:**\n\n${mainResponse}`;
      } else {
        // Only show main response, hide thinking process
        return mainResponse && mainResponse.length > 0 ? mainResponse : filteredText;
      }
    }
    
    // Fallback: if no </think> found, return as-is if showing thinking, or clean if not
    if (!showThinkingProcess) {
      filteredText = filteredText.replace(/<\/?think>/gi, '');
    }
    
    return filteredText.trim();
  }
  
  // For other models, apply normal filtering
  for (const pattern of modelConfig.cleanupPatterns) {
    filteredText = filteredText.replace(pattern, '');
  }
  
  // Remove thinking blocks (always for default, conditionally for deepseek)
  if (modelConfig.removeThinkingBlocks) {
    // Remove various thinking block patterns
    filteredText = filteredText.replace(/<thinking>[\s\S]*?<\/thinking>/gi, '');
    filteredText = filteredText.replace(/<\/?thinking>/gi, '');
    filteredText = filteredText.replace(/^<\/?thinking>?$/gi, '');
    filteredText = filteredText.replace(/<\/think>/gi, '');
    filteredText = filteredText.replace(/<think>/gi, '');
    filteredText = filteredText.replace(/\s*<\/think>\s*/gi, ' ');
    
    // Light deduplication - only remove consecutive identical sentences
    const sentences = filteredText.split(/(?<=[.!?])\s+/);
    const uniqueSentences = [];
    let lastSentence = '';
    for (const sentence of sentences) {
      const trimmed = sentence.trim();
      // Only remove if it's exactly the same as the previous sentence
      if (trimmed !== lastSentence && trimmed.length > 0) {
        uniqueSentences.push(sentence);
        lastSentence = trimmed;
      }
    }
    filteredText = uniqueSentences.join(' ');
  }
  
  // Remove verbose patterns and fix spacing issues
  if (modelConfig.removeVerbosePatterns) {
    // Clean up messy output patterns
    filteredText = filteredText.replace(/\s*\|\s*\w+\s*\|\s*/gi, '');
    filteredText = filteredText.replace(/\s*(1\.|2\.|3\.)\s*Break down[\s\S]*?:/gi, '');
    filteredText = filteredText.replace(/\s*Analyze different aspects[\s\S]*?:/gi, '');
    filteredText = filteredText.replace(/\s*Consider pros and cons[\s\S]*?:/gi, '');
  }
  
  // Universal spacing fixes for all models
  filteredText = filteredText.replace(/([a-z])([A-Z])/g, '$1 $2');
  filteredText = filteredText.replace(/([.!?])([A-Z])/g, '$1 $2');
  filteredText = filteredText.replace(/([a-z])(!)/g, '$1 $2');
  filteredText = filteredText.replace(/(\w)(\?)/g, '$1 $2');
  
  // Clean up common ending markers
  filteredText = filteredText.replace(/^<<END>>|<<END>>$/g, '');
  filteredText = filteredText.replace(/^\s*END\s*$/gi, '');
  
  // Normalize whitespace
  filteredText = filteredText.replace(/\s+/g, ' ');
  filteredText = filteredText.replace(/\n{3,}/g, '\n\n');
  filteredText = filteredText.trim();
  
  return filteredText;
}

// Llava 1.5 processing (for default model)
function processLlavaStream(textChunk: string, model: string, isDeepThinking: boolean): string {
  // For default model streaming, preserve original formatting to maintain proper spacing
  if (model === 'default-model') {
    // Only apply minimal cleaning without affecting spacing
    let cleanedText = textChunk;
    
    // Remove only thinking blocks, preserve everything else
    cleanedText = cleanedText.replace(/<thinking>[\s\S]*?<\/thinking>/gi, '');
    cleanedText = cleanedText.replace(/<\/?thinking>/gi, '');
    cleanedText = cleanedText.replace(/<\/think>/gi, '');
    cleanedText = cleanedText.replace(/<think>/gi, '');
    
    // Return original text with minimal cleaning to preserve streaming format
    return cleanedText;
  }
  
  // For other models, apply standard filtering
  return applyModelFilters(textChunk, model, false, false);
}

// DeepSeek R1 advanced processing (for deepseek model)
function processDeepSeekStream(textChunk: string, model: string, isDeepThinking: boolean, showThinkingProcess: boolean = false): string {
  // For DeepSeek R1, always return raw content - frontend will handle formatting
  return textChunk;
}

// Rate limiting in-memory store (for edge runtime)
const rateLimitStore = new Map<string, { count: number; resetTime: number }>();
const RATE_LIMIT_WINDOW = 60000; // 1 minute
const RATE_LIMIT_MAX_REQUESTS = 30; // 30 requests per minute

function checkRateLimit(clientId: string): boolean {
  const now = Date.now();
  const clientData = rateLimitStore.get(clientId);
  
  if (!clientData || now > clientData.resetTime) {
    rateLimitStore.set(clientId, { count: 1, resetTime: now + RATE_LIMIT_WINDOW });
    return true;
  }
  
  if (clientData.count >= RATE_LIMIT_MAX_REQUESTS) {
    return false;
  }
  
  clientData.count++;
  return true;
}

function getClientId(request: Request): string {
  // In a real application, you might use IP address or authenticated user ID
  return request.headers.get('x-forwarded-for') || 
         request.headers.get('x-real-ip') || 
         'unknown';
}

export async function POST(req: NextRequest) {
  const startTime = Date.now();
  const clientId = getClientId(req);
  
  try {
    // Rate limiting
    if (!checkRateLimit(clientId)) {
      apiLogger.warn('Rate limit exceeded', { clientId });
      return new Response("Rate limit exceeded. Please try again later.", { 
        status: 429,
        headers: {
          'Retry-After': '60',
          'X-RateLimit-Limit': RATE_LIMIT_MAX_REQUESTS.toString(),
          'X-RateLimit-Remaining': '0',
          'X-RateLimit-Reset': Math.ceil(Date.now() / 1000 + 60).toString()
        }
      });
    }

    apiLogger.debug('Starting request processing', { clientId });
    
    let requestBody: any;
    try {
      requestBody = await req.json();
    } catch (parseError) {
      apiLogger.error('Invalid JSON in request body', parseError);
      return new Response("Invalid JSON format", { status: 400 });
    }

    const { message, messages, model, useDeepThinking = false, isDeepThinking = false, showThinkingProcess = true, cortensorSessionId, environment: requestEnvironment, rawOutput = false } = requestBody;
    
    // Handle both single message and messages array formats
    let userMessage = '';
    if (message && typeof message === 'string') {
      userMessage = message.trim();
      apiLogger.debug('Using single message format', { messageLength: userMessage.length });
    } else if (messages && Array.isArray(messages) && messages.length > 0) {
      const lastUserMessage = messages.filter(m => m.role === 'user').pop();
      userMessage = lastUserMessage?.content?.trim() || '';
      apiLogger.debug('Using messages array format', { messageCount: messages.length });
    }
    
    if (!userMessage) {
      apiLogger.warn('No valid message provided');
      return new Response("No valid message provided.", { status: 400 });
    }

    if (userMessage.length > 10000) { // 10k character limit
      apiLogger.warn('Message too long', { length: userMessage.length });
      return new Response("Message too long. Please keep it under 10,000 characters.", { status: 400 });
    }

    // Determine deep thinking mode
    const deepThinking = useDeepThinking || isDeepThinking;

    // Get environment-specific configuration from .env.local and environment-config
    const headersList = await headers();
    let environment = requestEnvironment || headersList.get('x-chat-environment') || 'devnet6'; // Default devnet6 sesuai .env.local
    
    // Validate environment value
    if (environment !== 'testnet' && environment !== 'devnet6') {
      environment = 'devnet6'; // Default devnet6 sesuai .env.local
    }
    
    // Debug logging untuk environment detection
    apiLogger.debug('Environment configuration', {
      environment,
      source: requestEnvironment ? 'request-body' : 'header'
    });
    
    // Use environment configuration from environment-config.ts yang sudah mengikuti .env.local
    const { getEnvironmentValues } = await import('../../../lib/environment-config');
    const envConfig = getEnvironmentValues();

    let sessionId = envConfig.defaultSession;
    let isDeepseekR1 = false;
    let isLlama3_1 = false;
    
    apiLogger.debug('Model configuration', {
      selectedModel: model,
      environment,
      useDeepThinking: deepThinking
    });

    if (model === 'deepseek-r1') {
      sessionId = envConfig.deepseekSession;
      isDeepseekR1 = true;
      apiLogger.debug('Using Deepseek R1 mode');
    } else if (model === 'meta-llama-3.1') {
      sessionId = envConfig.llamaSession;
      isLlama3_1 = true;
      apiLogger.debug('Using Meta-Llama-3.1 mode');
    } else {
      apiLogger.debug('Using Default model (Llava 1.5)');
    }

    // Determine which prompt to use
    let systemPrompt: string;
    const maxTokens = 20000;

    if (isDeepseekR1) {
      if (deepThinking) {
        systemPrompt = appConfig.prompts.deepThinking.systemPrompt;
      } else {
        systemPrompt = appConfig.prompts.deepseekR1.systemPrompt;
      }
    } else if (isLlama3_1) {
      systemPrompt = appConfig.prompts.llama3_1.systemPrompt;
    } else {
      // Default model ALWAYS uses basic deep thinking for clean output
      systemPrompt = appConfig.prompts.default.systemPrompt;
    }

    // Format prompt
    const clientReference = `${Date.now()}${Math.random().toString(36).substr(2, 9)}`;
    const formattedPrompt = systemPrompt + '\n<|USER|>\n' + userMessage + '\n<|ASSISTANT|>\n';

    const apiUrl = `${envConfig.cortensorUrl}/api/v1/completions`;
    const apiKey = envConfig.cortensorApiKey;

    // Log final configuration untuk debugging
    apiLogger.debug('API Configuration', {
      environment,
      apiUrl,
      sessionId
    });

    if (!apiUrl) {
      apiLogger.error('API URL not configured');
      return new Response("Service configuration error", { status: 500 });
    }

    if (!apiKey) {
      apiLogger.error('API Key not configured');
      return new Response("Service configuration error", { status: 500 });
    }

    const payload = {
      session_id: parseInt(sessionId, 10),
      prompt: formattedPrompt,
      prompt_type: 1,
      prompt_template: "",
      stream: true, // Enable streaming for real-time text extraction
      timeout: parseInt(process.env.LLM_TIMEOUT || process.env.LLM_DEFAULT_TIMEOUT || '360', 10),
      client_reference: clientReference,
      max_tokens: maxTokens,
      temperature: 0.7,
      top_p: 0.95,
      top_k: 40,
      presence_penalty: 0,
      frequency_penalty: 0
    };
    
    apiLogger.debug('Making request to Cortensor API', {
      sessionId: payload.session_id,
      maxTokens: payload.max_tokens,
      timeout: payload.timeout,
      isStreaming: payload.stream,
      rawOutputDefault: true,
      streamingDisabled: 'Always disabled - RAW JSON is default for all models'
    });

    let cortensorResponse: Response;
    try {
      apiLogger.debug('Making request to Cortensor', {
        url: apiUrl,
        sessionId: payload.session_id,
        environment
      });
      
      cortensorResponse = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`,
          'Accept': 'text/event-stream', // Use streaming for real-time text extraction
          'Connection': 'keep-alive',
        },
        body: JSON.stringify(payload),
      });
    } catch (fetchError) {
      apiLogger.error('Failed to connect to Cortensor API', fetchError);
      return new Response("External service unavailable", { status: 503 });
    }

    if (!cortensorResponse.ok) {
      apiLogger.error('Cortensor API returned error', {
        status: cortensorResponse.status,
        statusText: cortensorResponse.statusText
      });
      return new Response(`External service error: ${cortensorResponse.status}`, { status: 502 });
    }

    if (!cortensorResponse.body) {
      apiLogger.error('No response body from Cortensor API');
      return new Response("No response from external service", { status: 502 });
    }

    apiLogger.info('Successfully connected to Cortensor API', {
      status: cortensorResponse.status,
      headers: Object.fromEntries(cortensorResponse.headers.entries()),
      processingTime: Date.now() - startTime
    });

    // Handle streaming response with text extraction
    try {
      // Check if response is actually streaming or JSON
      const contentType = cortensorResponse.headers.get('content-type') || '';
      const isStreamingResponse = contentType.includes('text/event-stream') || contentType.includes('application/stream');
      
      apiLogger.info('Response analysis', {
        contentType,
        isStreamingResponse,
        hasBody: !!cortensorResponse.body,
        responseHeaders: Object.fromEntries(cortensorResponse.headers.entries())
      });
      
      // First, let's get the raw response to debug what we're actually receiving
      const responseText = await cortensorResponse.text();
      apiLogger.info('Raw response from Cortensor', {
        responseLength: responseText.length,
        responsePreview: responseText.substring(0, 500) + (responseText.length > 500 ? '...' : ''),
        isJSON: responseText.trim().startsWith('{')
      });
      
      if (!isStreamingResponse) {
        // Handle non-streaming JSON response and convert to streaming format
        apiLogger.info('Converting JSON response to streaming format');
        
        let jsonResponse;
        try {
          jsonResponse = JSON.parse(responseText);
        } catch (parseError) {
          apiLogger.error('Failed to parse response as JSON', { 
            parseError, 
            responseText: responseText.substring(0, 1000) 
          });
          throw new Error('Invalid JSON response from API');
        }
        
        apiLogger.debug('Parsed JSON response', { 
          hasChoices: !!jsonResponse.choices,
          responseKeys: Object.keys(jsonResponse),
          fullResponse: jsonResponse
        });
        
        // Extract text content from JSON response
        let textContent = '';
        if (jsonResponse.choices && jsonResponse.choices[0]) {
          const choice = jsonResponse.choices[0];
          if (choice.text) {
            textContent = choice.text;
            apiLogger.info('Extracted text from choices[0].text', { textLength: textContent.length });
          } else if (choice.message && choice.message.content) {
            textContent = choice.message.content;
            apiLogger.info('Extracted text from choices[0].message.content', { textLength: textContent.length });
          }
        } else if (jsonResponse.response) {
          textContent = jsonResponse.response;
          apiLogger.info('Extracted text from response field', { textLength: textContent.length });
        } else if (jsonResponse.content) {
          textContent = jsonResponse.content;
          apiLogger.info('Extracted text from content field', { textLength: textContent.length });
        } else if (typeof jsonResponse === 'string') {
          textContent = jsonResponse;
          apiLogger.info('Using response as direct text', { textLength: textContent.length });
        }
        
        if (!textContent) {
          apiLogger.error('No text content found in response', { 
            availableKeys: Object.keys(jsonResponse),
            sampleResponse: jsonResponse
          });
          throw new Error('No text content found in API response');
        }
        
        // Apply model filters
        const filteredText = applyModelFilters(textContent, model, deepThinking, showThinkingProcess);
        apiLogger.info('Text filtering completed', { 
          originalLength: textContent.length,
          filteredLength: filteredText.length
        });
        
        // Create streaming format response
        const stream = new ReadableStream({
          start(controller) {
            // Send the complete text as streaming chunks
            const words = filteredText.split(' ');
            let currentIndex = 0;
            
            apiLogger.info('Starting streaming simulation', { totalWords: words.length });
            
            const sendChunk = () => {
              if (currentIndex < words.length) {
                const chunk = words[currentIndex] + ' ';
                const sseData = `data: ${JSON.stringify({ 
                  content: chunk,
                  id: 'stream',
                  object: 'chat.completion.chunk',
                  created: Date.now(),
                  model: model,
                  choices: [{
                    delta: { content: chunk },
                    index: 0,
                    finish_reason: null
                  }]
                })}\n\n`;
                
                controller.enqueue(new TextEncoder().encode(sseData));
                currentIndex++;
                
                // Continue streaming with small delay for natural typing effect
                setTimeout(sendChunk, 50);
              } else {
                // Send final done message
                controller.enqueue(new TextEncoder().encode('data: [DONE]\n\n'));
                controller.close();
                
                apiLogger.info('Streaming simulation completed', {
                  wordsStreamed: words.length,
                  processingTime: Date.now() - startTime
                });
              }
            };
            
            sendChunk();
          }
        });
        
        return new Response(stream, {
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'X-Response-Type': 'text-stream',
          },
        });
      }
      
      // Handle actual streaming response (if Cortensor returns SSE)
      apiLogger.info('Processing response as streaming SSE format');
      
      const stream = new ReadableStream({
        async start(controller) {
          try {
            // Since we already read the response, we need to process it directly
            const lines = responseText.split('\n');
            
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const eventData = line.slice(6);
                
                if (eventData === '[DONE]') {
                  controller.close();
                  return;
                }
                
                if (eventData.trim()) {
                  try {
                    const parsed = JSON.parse(eventData);
                    apiLogger.debug('Parsing SSE chunk', { 
                      id: parsed.id,
                      hasChoices: !!parsed.choices,
                      choicesLength: parsed.choices?.length
                    });
                    
                    // Extract text content from Cortensor's SSE format
                    let textContent = '';
                    if (parsed.choices && parsed.choices[0]) {
                      const choice = parsed.choices[0];
                      
                      // Cortensor uses "text" field for streaming content
                      if (typeof choice.text === 'string') {
                        textContent = choice.text;
                        apiLogger.debug('Extracted text from choice.text', { 
                          textContent: textContent,
                          textLength: textContent.length
                        });
                      }
                      // Fallback to other possible fields
                      else if (choice.delta && choice.delta.content) {
                        textContent = choice.delta.content;
                      }
                      else if (choice.message && choice.message.content) {
                        textContent = choice.message.content;
                      }
                    }
                    
                    // Only send if we have text content
                    if (textContent) {
                      // Apply model-specific processing for streaming
                      let filteredText = textContent;
                      let finalText = textContent; // Use original text by default
                      
                      if (model === 'deepseek-r1') {
                        filteredText = processDeepSeekStream(textContent, model, deepThinking, showThinkingProcess);
                        finalText = filteredText;
                      } else {
                        // For default model, preserve original text for proper streaming format
                        filteredText = processLlavaStream(textContent, model, deepThinking);
                        finalText = textContent; // Use original text to preserve spacing
                      }
                      
                      apiLogger.debug('Streaming text processing', { 
                        originalText: textContent,
                        filteredText: filteredText,
                        finalText: finalText,
                        model: model,
                        showThinkingProcess: showThinkingProcess
                      });
                      
                      // Create SSE format for frontend (convert to OpenAI-like format)
                      const sseData = `data: ${JSON.stringify({ 
                        content: finalText,
                        id: parsed.id || 'stream',
                        object: 'chat.completion.chunk',
                        created: parsed.created || Date.now(),
                        model: parsed.model || model,
                        choices: [{
                          delta: { content: finalText },
                          index: 0,
                          finish_reason: parsed.choices[0]?.finish_reason || null
                        }]
                      })}\n\n`;
                      
                      controller.enqueue(new TextEncoder().encode(sseData));
                      
                      apiLogger.debug('Sent streaming chunk to frontend', { 
                        finalTextLength: finalText.length,
                        filteredTextLength: filteredText.length,
                        originalTextLength: textContent.length
                      });
                    }
                  } catch (parseError) {
                    apiLogger.warn('Error parsing streaming data chunk', { 
                      parseError: parseError instanceof Error ? parseError.message : String(parseError),
                      eventData: eventData.substring(0, 200)
                    });
                    // Continue processing other messages
                  }
                }
              }
            }
            
            // Send final done message
            controller.enqueue(new TextEncoder().encode('data: [DONE]\n\n'));
            controller.close();
            
            apiLogger.info('Streaming completed successfully', {
              processingTime: Date.now() - startTime
            });
            
          } catch (error) {
            apiLogger.error('Streaming error', error);
            controller.error(error);
          }
        }
      });
      
      return new Response(stream, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, Authorization',
          'X-Response-Type': 'text-stream',
        },
      });
    } catch (streamError) {
      apiLogger.error('Failed to process streaming response', streamError);
      return new Response("Failed to process streaming response", { status: 502 });
    }

  } catch (error) {
    apiLogger.error('API Error', { 
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
      clientId,
      processingTime: Date.now() - startTime
    });
    
    return new Response("Internal server error", { 
      status: 500,
      headers: {
        'Content-Type': 'text/plain',
      }
    });
  }
}
