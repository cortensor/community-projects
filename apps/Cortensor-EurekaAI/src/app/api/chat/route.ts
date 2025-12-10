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
      /<\|USER\|>/gi,
      /<\|ASSISTANT\|>/gi,
      /<\/s>/gi,
      /USER[\s\S]*?ASSISTANT/gi,
      /^\s*user\s*:/gi,
      /^\s*assistant\s*:/gi,
    ],
    preserveCodeBlocks: true
  },
  'deepseek-r1': {
    name: 'Deepseek R1', 
    removeThinkingBlocks: true, // Remove thinking blocks
    removeVerbosePatterns: true,
    cleanupPatterns: [
      /<thinking>[\s\S]*?<\/thinking>/gi,
      /<\/?thinking>/gi,
      /^<\/?thinking>?$/gi,
      /<\/think>/gi, // Remove stray </think> tags
      /<think>/gi,   // Remove stray <think> tags
      /\s*<\/think>\s*/gi, // Remove </think> with surrounding whitespace
      // LLaMA-style special tokens that may appear in distill outputs
      /<\|begin_of_text\|>/gi,
      /<\|end_of_text\|>/gi,
      /<\|start_header_id\|>[\s\S]*?<\|end_header_id\|>/gi,
      /<\|eot_id\|>/gi,
      /<\|USER\|>[\s\S]*?<\|ASSISTANT\|>/gi,
      /<\|USER\|>/gi,
      /<\|ASSISTANT\|>/gi,
      /^\s*assistant\s*:/gi,
      /^\s*user\s*:/gi,
    ],
    preserveCodeBlocks: true
  },
  'llama-3.1-8b-q4': {
    name: 'Llama 3.1 8B Q4',
    removeThinkingBlocks: true,
    removeVerbosePatterns: true,
    cleanupPatterns: [
      /<\|begin_of_text\|>/gi,
      /<\|end_of_text\|>/gi,
      /<\|start_header_id\|>[\s\S]*?<\|end_header_id\|>/gi,
      /<\|eot_id\|>/gi,
      /<\|USER\|>[\s\S]*?<\|ASSISTANT\|>/gi,
      /<\|USER\|>/gi,
      /<\|ASSISTANT\|>/gi,
      /<\/s>/gi,
      /^\s*assistant\s*:/gi,
      /^\s*user\s*:/gi,
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
  // First, remove any leaked LLaMA special tokens and headers
    filteredText = filteredText.replace(/<\|begin_of_text\|>|<\|end_of_text\|>|<\|eot_id\|>/gi, '');
    filteredText = filteredText.replace(/<\|start_header_id\|>[\s\S]*?<\|end_header_id\|>/gi, '');
  filteredText = filteredText.replace(/<\|USER\|>[\s\S]*?<\|ASSISTANT\|>/gi, '');
  filteredText = filteredText.replace(/<\|USER\|>/gi, '');
  filteredText = filteredText.replace(/<\|ASSISTANT\|>/gi, '');
  filteredText = filteredText.replace(/^\s*assistant\s*:/gi, '');
  filteredText = filteredText.replace(/^\s*user\s*:/gi, '');

    // If output contains multiple turns, keep ONLY the last assistant/user segment
    const findLastIndex = (text: string, patterns: RegExp[]): { idx: number; len: number } => {
      let last = -1; let len = 0;
      for (const p of patterns) {
        let m: RegExpExecArray | null;
        const r = new RegExp(p.source, p.flags.includes('g') ? p.flags : p.flags + 'g');
        while ((m = r.exec(text)) !== null) {
          last = m.index; len = m[0].length;
        }
      }
      return { idx: last, len };
    };
    const lastAssistant = findLastIndex(filteredText, [/<\|ASSISTANT\|>/i, /\n\s*Assistant\s*:/i]);
    const lastUser = findLastIndex(filteredText, [/<\|USER\|>/i, /\n\s*User\s*:/i]);
    let startFrom = 0;
    if (lastAssistant.idx >= 0) startFrom = lastAssistant.idx + lastAssistant.len;
    else if (lastUser.idx >= 0) startFrom = lastUser.idx + lastUser.len;
    if (startFrom > 0) {
      filteredText = filteredText.slice(startFrom).trimStart();
    }

    // Prefer post-</think> when present; otherwise keep pre-<think> content as the answer
    const thinkStartIndex = filteredText.indexOf('<think>');
    const thinkEndIndex = filteredText.indexOf('</think>');
    
    if (thinkEndIndex !== -1) {
  // Extract thinking process (from start to </think>)
  let thinkingContent = filteredText.substring(0, thinkEndIndex).trim();
      // Clean stray markers inside thinking
      thinkingContent = thinkingContent
        .replace(/^<think>\s*/i, '')
        .replace(/<\|USER\|>|<\|ASSISTANT\|>/gi, '')
        .replace(/^\s*(user|assistant)\s*:\s*/gi, '')
        .replace(/<\|begin_of_text\|>|<\|end_of_text\|>|<\|eot_id\|>/gi, '')
        .replace(/<｜end▁of▁sentence｜>/g, '')
        .replace(/<\|end_of_sentence\|>/g, '')
        .trim();
    // Extract main response (after </think>)
    const mainResponse = filteredText.substring(thinkEndIndex + 8).trim(); // 8 = length of '</think>'
      
      if (showThinkingProcess && thinkingContent && thinkingContent.length > 0) {
        // Show thinking process with cleaner section headers
        return `🧠 Thinking Process\n\n${thinkingContent}\n\n---\n\nResponse\n\n${mainResponse}`;
      } else {
        // Only show main response, hide thinking process
        return mainResponse && mainResponse.length > 0 ? mainResponse : filteredText;
      }
    }
    
    // Fallback: if no </think> found, return as-is if showing thinking, or clean if not
    if (!showThinkingProcess) {
      filteredText = filteredText.replace(/<\/??think>/gi, '');
    }
    
    return filteredText.trim();
  }
  
  // For other models, apply normal filtering
  for (const pattern of modelConfig.cleanupPatterns) {
    filteredText = filteredText.replace(pattern, '');
  }
  // Remove end-of-sentence marker variants globally
  filteredText = filteredText.replace(/<｜end▁of▁sentence｜>/g, '');
  filteredText = filteredText.replace(/<\|end_of_sentence\|>/g, '');
  // Remove generic EOS `</s>` used by some LLMs
  filteredText = filteredText.replace(/<\/s>/gi, '');
  
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

// Relevance filter: remove echoed user question, role markers, and repeated sentences
function enforceRelevanceAndDedup(answerText: string, userMessage: string): string {
  try {
    let text = String(answerText || '');
    const norm = (s: string) => s.toLowerCase()
      .replace(/<\|user\|>|<\|assistant\|>/gi, '')
      .replace(/user\s*:|assistant\s*:/gi, '')
      .replace(/[^a-z0-9]+/gi, ' ')
      .trim();

    const userNorm = norm(userMessage || '');

    // Remove obvious context/preamble lines
    text = text
      .replace(/^as an ai[\s\S]*?\.?\s*/gi, '')
      .replace(/^as a language model[\s\S]*?\.?\s*/gi, '')
      .replace(/^context\s*:\s*[\s\S]*?\n/gi, '')
      .replace(/^q\s*:\s*/gim, '')
      .replace(/^a\s*:\s*/gim, '');

    // Split into sentences while preserving order
    const sentences = text
      .split(/(?<=[.!?])\s+/)
      .map(s => s.trim())
      .filter(Boolean);

    const seen = new Set<string>();
    const result: string[] = [];

    for (const s of sentences) {
      const sNorm = norm(s);
      // Drop if it's the same as the user's question or contains it heavily
      if (sNorm === userNorm) continue;
      if (userNorm && sNorm.length > 0 && (sNorm.includes(userNorm) || userNorm.includes(sNorm))) continue;
      // Deduplicate globally by normalized sentence
      if (seen.has(sNorm)) continue;
      seen.add(sNorm);
      result.push(s);
    }

    // If still very long with many sentences, keep first 3 for relevance
    if (result.length > 3) {
      return result.slice(0, 3).join(' ').trim();
    }
    return result.join(' ').trim();
  } catch {
    return String(answerText || '').trim();
  }
}

// Llava 1.5 processing (for default model)
function processLlavaStream(textChunk: string, model: string, isDeepThinking: boolean): string {
  // For default and llama models streaming, preserve original formatting to maintain proper spacing
  if (model === 'default-model' || model === 'llama-3.1-8b-q4') {
    // Only apply minimal cleaning without affecting spacing
    let cleanedText = textChunk;
    
    // Remove only thinking blocks, preserve everything else
    cleanedText = cleanedText.replace(/<thinking>[\s\S]*?<\/thinking>/gi, '');
    cleanedText = cleanedText.replace(/<\/?thinking>/gi, '');
    cleanedText = cleanedText.replace(/<\/think>/gi, '');
    cleanedText = cleanedText.replace(/<think>/gi, '');
    // Remove llama special tokens if they leak into chunks
  cleanedText = cleanedText.replace(/<\|begin_of_text\|>|<\|end_of_text\|>|<\|eot_id\|>/gi, '');
  cleanedText = cleanedText.replace(/<\|start_header_id\|>[\s\S]*?<\|end_header_id\|>/gi, '');
  cleanedText = cleanedText.replace(/<\/s>/gi, '');
  // Remove end-of-sentence markers
  cleanedText = cleanedText.replace(/<｜end▁of▁sentence｜>/g, '');
  cleanedText = cleanedText.replace(/<\|end_of_sentence\|>/g, '');
    
    // Return original text with minimal cleaning to preserve streaming format
    return cleanedText;
  }
  
  // For other models, apply standard filtering
  return applyModelFilters(textChunk, model, false, false);
}

// DeepSeek R1 advanced processing (for deepseek model)
function processDeepSeekStream(textChunk: string, model: string, isDeepThinking: boolean, showThinkingProcess: boolean = false): string {
  let cleaned = textChunk;
  // If not showing thinking, remove <think> blocks and tags
  if (!showThinkingProcess) {
    cleaned = cleaned.replace(/<thinking>[\s\S]*?<\/thinking>/gi, '');
    cleaned = cleaned.replace(/<\/?thinking>/gi, '');
    cleaned = cleaned.replace(/<\/think>/gi, '');
    cleaned = cleaned.replace(/<think>/gi, '');
    cleaned = cleaned.replace(/\s*<\/think>\s*/gi, ' ');
  }
  // Remove any leaked LLaMA special tokens
  cleaned = cleaned.replace(/<\|begin_of_text\|>|<\|end_of_text\|>|<\|eot_id\|>/gi, '');
  cleaned = cleaned.replace(/<\|start_header_id\|>[\s\S]*?<\|end_header_id\|>/gi, '');
  cleaned = cleaned.replace(/<\/s>/gi, '');
  cleaned = cleaned.replace(/<\|USER\|>[\s\S]*?<\|ASSISTANT\|>/gi, '');
  cleaned = cleaned.replace(/^\s*assistant\s*:/gi, '');
  // Remove end-of-sentence markers
  cleaned = cleaned.replace(/<｜end▁of▁sentence｜>/g, '');
  cleaned = cleaned.replace(/<\|end_of_sentence\|>/g, '');
  // If role markers for a new turn are present in a chunk, truncate before them to avoid cross-turn bleed
  const roleCut = cleaned.match(/<\|USER\|>|<\|ASSISTANT\|>|\n\s*User\s*:|\n\s*Assistant\s*:/i);
  if (roleCut && roleCut.index !== undefined && roleCut.index >= 0) {
    cleaned = cleaned.slice(0, roleCut.index);
  }
  return cleaned;
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

    const { 
      message, 
      messages, 
      model, 
      useDeepThinking = false, 
      isDeepThinking = false, 
      showThinkingProcess = true, 
      cortensorSessionId, 
      environment: requestEnvironment, 
      rawOutput = false,
      enableMemory = false,
      chatHistory = [],
      nonStreaming = false
    } = requestBody;
    
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
    } else if (model === 'llama-3.1-8b-q4') {
      sessionId = envConfig.llamaSession;
      isLlama3_1 = true;
      apiLogger.debug('Using Llama 3.1 mode');
    } else {
      apiLogger.debug('Using Default model (Llava 1.5)');
    }

  // Determine which prompt to use
    let systemPrompt: string;
  // Use a lower token cap for DeepSeek to encourage concise answers
  const maxTokens = isDeepseekR1 ? 2048 : 20000;

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

    // Helpers: sanitize previous contents from leaked control tokens before re-injecting
    const sanitizeForPrompt = (text: string): string => {
      let t = String(text ?? '');
      // strip known special/control tokens and thinking tags that could confuse the new turn
      t = t.replace(/<\|begin_of_text\|>|<\|end_of_text\|>|<\|eot_id\|>/gi, '');
      t = t.replace(/<\|start_header_id\|>[\s\S]*?<\|end_header_id\|>/gi, '');
  t = t.replace(/<\|USER\|>|<\|ASSISTANT\|>/gi, '');
  t = t.replace(/<\/s>/gi, '');
      t = t.replace(/<thinking>[\s\S]*?<\/thinking>/gi, '');
      t = t.replace(/<\/?thinking>/gi, '');
      t = t.replace(/<\/think>/gi, '');
      t = t.replace(/<think>/gi, '');
      t = t.replace(/<｜end▁of▁sentence｜>/g, '');
      t = t.replace(/<\|end_of_sentence\|>/g, '');
      return t.trim();
    };

    // Build history chunk if Memory Mode is enabled
    let historyPrompt = '';
    if (enableMemory && Array.isArray(chatHistory) && chatHistory.length > 0) {
      // Keep only {role, content} pairs for user/assistant, drop system or others
      type ChatMsg = { role: string; content: string };
      const cleaned: ChatMsg[] = (chatHistory as ChatMsg[])
        .filter(m => m && typeof m.content === 'string' && (m.role === 'user' || m.role === 'assistant'))
        // prevent duplicates or empty
        .map(m => ({ role: m.role, content: sanitizeForPrompt(m.content) }))
        .filter(m => m.content.length > 0);

      // Cap history to avoid overly long prompts: last 12 messages or ~6000 chars
      const MAX_MSGS = 12;
      const sliced = cleaned.slice(-MAX_MSGS);
      // Additionally cap by characters
      const MAX_CHARS = 6000;
      let running = '';
      for (const m of sliced) {
        const chunk = `${m.role === 'assistant' ? '<|ASSISTANT|>' : '<|USER|>'}\n${m.content}\n`;
        if ((running.length + chunk.length) > MAX_CHARS) break;
        running += chunk;
      }
      historyPrompt = running;
    }

    // Format final prompt with optional memory
    const clientReference = `${Date.now()}${Math.random().toString(36).substr(2, 9)}`;
    const formattedPrompt = `${systemPrompt}\n${historyPrompt}${historyPrompt ? '' : ''}<|USER|>\n${sanitizeForPrompt(userMessage)}\n<|ASSISTANT|>\n`;

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
      stream: nonStreaming ? false : true, // Allow client to disable streaming
      timeout: parseInt(process.env.LLM_TIMEOUT || process.env.LLM_DEFAULT_TIMEOUT || '360', 10),
      client_reference: clientReference,
      max_tokens: maxTokens,
      temperature: 0.7,
      top_p: 0.95,
      top_k: 40,
      presence_penalty: 0,
      frequency_penalty: 0,
      // Stop tokens to prevent the model from adding new user/assistant turns or leaking control tokens
  stop: ["\nUser:", "\nAssistant:", "<|eot_id|>", "<|USER|>", "<|ASSISTANT|>"]
    };
    
    apiLogger.debug('Making request to Cortensor API', {
      sessionId: payload.session_id,
      maxTokens: payload.max_tokens,
      timeout: payload.timeout,
      isStreaming: payload.stream,
      rawOutputDefault: true,
      streamingDisabled: nonStreaming ? 'Client requested non-streaming' : 'Always disabled - RAW JSON is default for all models',
      enableMemory,
      historyIncluded: historyPrompt.length > 0,
      historyLengthChars: historyPrompt.length
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
          'Accept': nonStreaming ? 'application/json' : 'text/event-stream', // Request JSON in non-streaming mode
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
      
      // If client asked nonStreaming, parse once and return JSON
      if (nonStreaming) {
        let jsonResponse: any;
        try {
          jsonResponse = JSON.parse(responseText);
        } catch (parseError) {
          apiLogger.error('Failed to parse non-streaming response as JSON', { parseError, preview: responseText.substring(0, 600) });
          return new Response("Invalid JSON from upstream", { status: 502 });
        }

        // Extract text content
        let textContent = '';
        if (jsonResponse.choices && jsonResponse.choices[0]) {
          const choice = jsonResponse.choices[0];
          if (typeof choice.text === 'string') textContent = choice.text;
          else if (choice.message?.content) textContent = choice.message.content;
        } else if (jsonResponse.response) {
          textContent = jsonResponse.response;
        } else if (jsonResponse.content) {
          textContent = jsonResponse.content;
        } else if (typeof jsonResponse === 'string') {
          textContent = jsonResponse;
        }

        if (!textContent) {
          apiLogger.error('No text content in non-streaming response', { keys: Object.keys(jsonResponse) });
          return new Response("No content from upstream", { status: 502 });
        }

        // For DeepSeek, split thinking and answer for UI
        let thinkingContent: string | undefined = undefined;
        let answerText = textContent;

        if (model === 'deepseek-r1') {
          // Pre-clean tokens first
          let cleaned = textContent
            .replace(/<\|begin_of_text\|>|<\|end_of_text\|>|<\|eot_id\|>/gi, '')
            .replace(/<\|start_header_id\|>[\s\S]*?<\|end_header_id\|>/gi, '')
            .replace(/<\/s>/gi, '')
            .replace(/<\|USER\|>[\s\S]*?<\|ASSISTANT\|>/gi, '')
            .replace(/<｜end▁of▁sentence｜>/g, '')
            .replace(/<\|end_of_sentence\|>/g, '');
          // If any role markers for a new turn appear, hard truncate before them
          const roleMarkerIdx = (() => {
            const m = cleaned.match(/<\|USER\|>|<\|ASSISTANT\|>|\n\s*User\s*:|\n\s*Assistant\s*:/i);
            return m && m.index !== undefined ? m.index : -1;
          })();
          if (roleMarkerIdx > -1) {
            cleaned = cleaned.slice(0, roleMarkerIdx);
          }
          // If output contains multiple turns, select the last assistant/user segment
          const findLastIndex = (text: string, patterns: RegExp[]): { idx: number; len: number } => {
            let last = -1; let len = 0;
            for (const p of patterns) {
              let m: RegExpExecArray | null;
              const r = new RegExp(p.source, p.flags.includes('g') ? p.flags : p.flags + 'g');
              while ((m = r.exec(text)) !== null) { last = m.index; len = m[0].length; }
            }
            return { idx: last, len };
          };
          const lastAssistant = findLastIndex(cleaned, [/<\|ASSISTANT\|>/i, /\n\s*Assistant\s*:/i]);
          const lastUser = findLastIndex(cleaned, [/<\|USER\|>/i, /\n\s*User\s*:/i]);
          let segment = cleaned;
          if (lastAssistant.idx >= 0) segment = cleaned.slice(lastAssistant.idx + lastAssistant.len);
          else if (lastUser.idx >= 0) segment = cleaned.slice(lastUser.idx + lastUser.len);

          // Extract think/answer from the chosen segment
          const startIdx = segment.indexOf('<think>');
          const idx = segment.indexOf('</think>');
          if (idx > -1) {
            // Prefer post-think as final answer; keep pre-think text only for thinking panel
            thinkingContent = (startIdx > -1 ? segment.substring(startIdx, idx) : segment.substring(0, idx))
              .replace(/^<think>\s*/i, '')
              .replace(/<\|USER\|>|<\|ASSISTANT\|>/gi, '')
              .replace(/^\s*(user|assistant)\s*:\s*/gi, '')
              .trim();
            answerText = segment.substring(idx + 8).trim();
          } else {
            // No explicit think block; show entire content as answer
            answerText = segment.trim();
          }
          // Finally apply generic filters to the answer and trim for conciseness
          answerText = applyModelFilters(answerText, model, deepThinking, false);
          // Ensure relevance and remove echoed user question / duplicates
          answerText = enforceRelevanceAndDedup(answerText, userMessage);
          // Enforce concise style: collapse whitespace and limit to ~1200 chars
          answerText = answerText.replace(/\s+$/g, '').replace(/\n{3,}/g, '\n\n');
          if (answerText.length > 1200) {
            answerText = answerText.slice(0, 1200).trimEnd() + '…';
          }
        } else {
          answerText = applyModelFilters(textContent, model, deepThinking, showThinkingProcess);
          answerText = enforceRelevanceAndDedup(answerText, userMessage);
        }

        const body = JSON.stringify({ content: answerText, thinkingContent });
        return new Response(body, {
          headers: { 'Content-Type': 'application/json' }
        });
      }

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
                      } else if (model === 'llama-3.1-8b-q4') {
                        // For Llama 3.1 variants, use minimally cleaned text to avoid leaking special tokens
                        filteredText = processLlavaStream(textContent, model, deepThinking);
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
